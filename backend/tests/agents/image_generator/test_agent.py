import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.image_generator import (
    ImageGeneratorAgent,
    ImageGeneratorConfig,
    LocalStorage,
    ValidationError,
    GenerationError,
    APIError,
)


@pytest.fixture
def mock_openai_client():
    client = MagicMock()
    return client


@pytest.fixture
def mock_storage():
    storage = AsyncMock(spec=LocalStorage)
    storage.save = AsyncMock(return_value="https://example.com/image.png")
    return storage


@pytest.fixture
def agent(mock_openai_client, mock_storage):
    config = ImageGeneratorConfig(
        model="dall-e-3",
        size="1024x1024",
        batch_size=3,
        retry_attempts=2,
    )
    return ImageGeneratorAgent(
        openai_client=mock_openai_client,
        config=config,
        storage=mock_storage,
    )


@pytest.fixture
def sample_scene():
    return {
        "scene_id": 1,
        "description": "A beautiful sunset over mountains",
        "image_prompt": "anime style, beautiful sunset over mountains",
        "characters": ["hero"],
    }


@pytest.fixture
def sample_character_templates():
    return {
        "hero": {
            "name": "hero",
            "base_prompt": "young male warrior with sword",
            "visual_description": "anime style, young warrior",
        }
    }


@pytest.mark.asyncio
async def test_generate_success(agent, mock_openai_client, sample_scene, sample_character_templates):
    mock_response = MagicMock()
    mock_response.data = [MagicMock(url="https://example.com/generated.png")]
    mock_openai_client.images.generate = AsyncMock(return_value=mock_response)
    
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"\x89PNG" + b"\x00" * 2000)
        
        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value=mock_get)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        result = await agent.generate(sample_scene, sample_character_templates)
        
        assert result == "https://example.com/image.png"
        assert mock_openai_client.images.generate.called


@pytest.mark.asyncio
async def test_generate_with_retry(agent, mock_openai_client, sample_scene):
    mock_openai_client.images.generate = AsyncMock(
        side_effect=[Exception("API Error"), Exception("API Error"), MagicMock(
            data=[MagicMock(url="https://example.com/generated.png")]
        )]
    )
    
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"\x89PNG" + b"\x00" * 2000)
        
        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value=mock_get)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        with pytest.raises(GenerationError, match="Failed to generate image after"):
            await agent.generate(sample_scene)


@pytest.mark.asyncio
async def test_generate_batch(agent, mock_openai_client, sample_character_templates):
    scenes = [
        {"scene_id": 1, "image_prompt": "scene 1"},
        {"scene_id": 2, "image_prompt": "scene 2"},
        {"scene_id": 3, "image_prompt": "scene 3"},
    ]
    
    mock_response = MagicMock()
    mock_response.data = [MagicMock(url="https://example.com/generated.png")]
    mock_openai_client.images.generate = AsyncMock(return_value=mock_response)
    
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"\x89PNG" + b"\x00" * 2000)
        
        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value=mock_get)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        results = await agent.generate_batch(scenes, sample_character_templates)
        
        assert len(results) == 3
        assert all(r == "https://example.com/image.png" for r in results)


@pytest.mark.asyncio
async def test_generate_batch_with_errors(agent, mock_openai_client):
    scenes = [
        {"scene_id": 1, "image_prompt": "scene 1"},
        {"scene_id": 2, "image_prompt": "scene 2"},
    ]
    
    mock_openai_client.images.generate = AsyncMock(side_effect=Exception("API Error"))
    
    results = await agent.generate_batch(scenes)
    
    assert len(results) == 2
    assert all(r == "" for r in results)


def test_build_prompt(agent, sample_scene, sample_character_templates):
    prompt = agent._build_prompt(sample_scene, sample_character_templates)
    
    assert "beautiful sunset over mountains" in prompt
    assert "young male warrior with sword" in prompt or "young warrior" in prompt
    assert "anime style" in prompt


def test_build_prompt_without_characters(agent):
    scene = {
        "scene_id": 1,
        "image_prompt": "beautiful landscape",
        "characters": [],
    }
    
    prompt = agent._build_prompt(scene, {})
    
    assert "beautiful landscape" in prompt
    assert "anime style" in prompt


def test_build_prompt_missing_prompt(agent):
    scene = {
        "scene_id": 1,
        "characters": [],
    }
    
    with pytest.raises(ValidationError, match="must have 'image_prompt' or 'description'"):
        agent._build_prompt(scene, {})


def test_validate_scene_invalid_type(agent):
    with pytest.raises(ValidationError, match="must be a dictionary"):
        agent._validate_scene("not a dict")


def test_validate_scene_missing_prompt(agent):
    scene = {"scene_id": 1}
    
    with pytest.raises(ValidationError, match="must have 'image_prompt' or 'description'"):
        agent._validate_scene(scene)


def test_generate_filename(agent):
    scene = {"scene_id": 1, "id": "test-id"}
    
    filename = agent._generate_filename(scene)
    
    assert "scene_1" in filename
    assert filename.endswith(".png")


@pytest.mark.asyncio
async def test_generate_image_api_error(agent, mock_openai_client):
    mock_openai_client.images.generate = AsyncMock(side_effect=Exception("API Error"))
    
    with pytest.raises(APIError, match="Image generation API error"):
        await agent._generate_image("test prompt")


@pytest.mark.asyncio
async def test_generate_image_no_data(agent, mock_openai_client):
    mock_response = MagicMock()
    mock_response.data = []
    mock_openai_client.images.generate = AsyncMock(return_value=mock_response)
    
    with pytest.raises(APIError, match="Image generation API error"):
        await agent._generate_image("test prompt")


@pytest.mark.asyncio
async def test_download_image_http_error(agent):
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = MagicMock()
        mock_response.status = 404
        
        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value=mock_get)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        with pytest.raises(GenerationError, match="Failed to download image: HTTP 404"):
            await agent._download_image("https://example.com/image.png")


@pytest.mark.asyncio
async def test_download_image_too_small(agent):
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"small")
        
        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value=mock_get)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        with pytest.raises(GenerationError, match="too small"):
            await agent._download_image("https://example.com/image.png")
