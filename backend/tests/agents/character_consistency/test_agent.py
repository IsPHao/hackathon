import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_openai import ChatOpenAI

from src.agents.character_consistency import (
    CharacterConsistencyAgent,
    CharacterConsistencyConfig,
    CharacterTemplate,
    LocalFileStorage,
    ValidationError,
    GenerationError,
)


@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=ChatOpenAI)
    return llm


@pytest.fixture
def mock_storage():
    storage = AsyncMock(spec=LocalFileStorage)
    return storage


@pytest.fixture
def agent(mock_llm, mock_storage):
    config = CharacterConsistencyConfig(
        enable_caching=True,
        storage_base_path="test_data",
    )
    return CharacterConsistencyAgent(llm=mock_llm, storage=mock_storage, config=config)


@pytest.fixture
def sample_characters():
    return [
        {
            "name": "小明",
            "description": "一个16岁的高中生",
            "appearance": {
                "gender": "male",
                "age": 16,
                "hair": "短黑发",
                "eyes": "棕色眼睛",
                "clothing": "校服",
            },
        },
        {
            "name": "小红",
            "description": "一个16岁的女学生",
            "appearance": {
                "gender": "female",
                "age": 16,
                "hair": "长黑发扎成马尾",
                "eyes": "明亮的眼睛",
                "clothing": "校服",
            },
        }
    ]


@pytest.fixture
def sample_features_response():
    return {
        "base_prompt": "anime style, young male student, short black hair, brown eyes, school uniform",
        "negative_prompt": "low quality, blurry, distorted",
        "features": {
            "gender": "male",
            "age": "16",
            "hair": "short black hair",
            "eyes": "brown eyes",
            "clothing": "school uniform",
            "distinctive_features": "curious expression"
        }
    }


@pytest.mark.asyncio
async def test_manage_new_characters(agent, sample_characters, sample_features_response):
    agent.storage.load_character.return_value = None
    
    with patch.object(agent, '_extract_character_features', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = sample_features_response
        
        result = await agent.manage(sample_characters, project_id="test_project")
        
        assert len(result) == 2
        assert "小明" in result
        assert "小红" in result
        assert isinstance(result["小明"], CharacterTemplate)
        assert agent.storage.save_character.call_count == 2


@pytest.mark.asyncio
async def test_manage_existing_characters(agent, sample_characters):
    existing_data = {
        "name": "小明",
        "base_prompt": "existing prompt",
        "negative_prompt": "low quality",
        "features": {},
        "reference_image_url": None,
    }
    
    agent.storage.load_character.return_value = existing_data
    
    result = await agent.manage(sample_characters, project_id="test_project")
    
    assert len(result) == 2
    assert result["小明"].base_prompt == "existing prompt"


@pytest.mark.asyncio
async def test_character_template_creation():
    character_data = {
        "name": "测试角色",
        "base_prompt": "anime style, test character",
        "negative_prompt": "low quality",
        "features": {
            "gender": "male",
            "age": "20",
        },
        "reference_image_url": "https://example.com/image.png",
    }
    
    template = CharacterTemplate(character_data)
    
    assert template.name == "测试角色"
    assert template.base_prompt == "anime style, test character"
    assert template.reference_image_url == "https://example.com/image.png"
    assert template.seed > 0


def test_character_template_scene_prompt():
    character_data = {
        "name": "角色",
        "base_prompt": "anime style, character",
        "negative_prompt": "low quality",
        "features": {},
    }
    
    template = CharacterTemplate(character_data)
    scene_prompt = template.create_scene_prompt("standing in classroom")
    
    assert "anime style, character" in scene_prompt
    assert "standing in classroom" in scene_prompt


def test_character_template_to_dict():
    character_data = {
        "name": "角色",
        "base_prompt": "test prompt",
        "negative_prompt": "low quality",
        "features": {"gender": "male"},
        "reference_image_url": "url",
    }
    
    template = CharacterTemplate(character_data)
    result = template.to_dict()
    
    assert result["name"] == "角色"
    assert result["base_prompt"] == "test prompt"
    assert "seed" in result


@pytest.mark.asyncio
async def test_extract_character_features(agent, mock_llm, sample_features_response):
    mock_response = MagicMock()
    mock_response.content = json.dumps(sample_features_response)
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    agent.llm = mock_llm
    
    character_data = {
        "name": "测试",
        "description": "测试角色",
        "appearance": {"gender": "male"},
    }
    
    result = await agent._extract_character_features(character_data)
    
    assert result["base_prompt"] == sample_features_response["base_prompt"]
    assert "features" in result


@pytest.mark.asyncio
async def test_extract_character_features_json_error(agent, mock_llm):
    mock_response = MagicMock()
    mock_response.content = "invalid json"
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    agent.llm = mock_llm
    
    character_data = {
        "name": "测试",
        "description": "测试角色",
        "appearance": {},
    }
    
    with pytest.raises(GenerationError, match="Invalid JSON"):
        await agent._extract_character_features(character_data)


@pytest.mark.asyncio
async def test_save_reference_image(agent):
    project_id = "test_project"
    character_name = "角色"
    image_url = "https://example.com/image.png"
    
    await agent.save_reference_image(project_id, character_name, image_url)
    
    agent.storage.save_reference_image.assert_called_once_with(
        project_id, character_name, image_url
    )


@pytest.mark.asyncio
async def test_validate_input_empty_project_id(agent, sample_characters):
    with pytest.raises(ValidationError, match="project_id is required"):
        await agent.manage(sample_characters, project_id="")


@pytest.mark.asyncio
async def test_validate_input_empty_characters(agent):
    with pytest.raises(ValidationError, match="cannot be empty"):
        await agent.manage([], project_id="test_project")


@pytest.mark.asyncio
async def test_validate_input_invalid_type(agent):
    with pytest.raises(ValidationError, match="must be a list"):
        await agent.manage("not a list", project_id="test_project")


@pytest.mark.asyncio
async def test_caching_enabled(agent, sample_characters, sample_features_response):
    agent.storage.load_character.return_value = None
    
    with patch.object(agent, '_extract_character_features', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = sample_features_response
        
        await agent.manage([sample_characters[0]], project_id="test_project")
        await agent.manage([sample_characters[0]], project_id="test_project")
        
        assert agent.storage.load_character.call_count == 1


@pytest.mark.asyncio
async def test_build_base_prompt(agent):
    features_data = {
        "base_prompt": "custom prompt",
    }
    
    result = agent._build_base_prompt(features_data)
    assert result == "custom prompt"


@pytest.mark.asyncio
async def test_build_base_prompt_from_features(agent):
    features_data = {
        "features": {
            "gender": "male",
            "age": "20",
            "hair": "black hair",
            "eyes": "blue eyes",
        }
    }
    
    result = agent._build_base_prompt(features_data)
    assert "anime style" in result
    assert "male" in result
    assert "black hair" in result
