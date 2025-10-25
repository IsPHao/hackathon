import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from src.agents.image_generator import (
    ImageGeneratorAgent,
    ImageGeneratorConfig,
    ValidationError,
    GenerationError,
)


@pytest.fixture
def config():
    """Create ImageGeneratorConfig for testing"""
    return ImageGeneratorConfig(
        qiniu_api_key="test_api_key",
        model="qwen-image-plus",
        size="1024x1024",
        batch_size=3,
        retry_attempts=3,
        generation_mode="text2image"
    )


@pytest.fixture
def agent(config):
    """Create ImageGeneratorAgent"""
    return ImageGeneratorAgent(
        task_id="test-task-123",
        config=config,
    )


@pytest.fixture
def sample_scene():
    """Sample scene for image generation"""
    return {
        "scene_id": 1,
        "description": "A beautiful sunset over mountains",
        "image_prompt": "anime style, beautiful sunset over mountains",
        "characters": ["hero"],
    }


@pytest.mark.asyncio
async def test_generate_success(agent, sample_scene, sample_character_templates):
    """Test successful image generation"""
    # Mock the internal methods
    agent._generate_image_qiniu = AsyncMock(return_value=b"fake_image_data")
    agent.task_storage.save_image = AsyncMock(return_value="scene_1_test.png")
    
    result = await agent.generate(sample_scene, sample_character_templates)
    
    assert isinstance(result, str)
    assert "scene_1" in result
    agent._generate_image_qiniu.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_with_retry(agent, sample_scene):
    """Test retry mechanism"""
    # Mock the internal method to fail first, then succeed
    agent._generate_image_qiniu = AsyncMock(side_effect=[
        Exception("API Error"),
        Exception("API Error"),
        b"fake_image_data"  # Succeed on the third attempt
    ])
    agent.task_storage.save_image = AsyncMock(return_value="scene_1_test.png")
    
    result = await agent.generate(sample_scene)
    
    assert isinstance(result, str)
    assert agent._generate_image_qiniu.await_count == 3


@pytest.mark.asyncio
async def test_generate_batch(agent, sample_character_templates):
    """Test batch generation"""
    # Mock the internal methods
    agent._generate_image_qiniu = AsyncMock(return_value=b"fake_image_data")
    agent.task_storage.save_image = AsyncMock(return_value="scene_1_test.png")
    
    scenes = [
        {"scene_id": 1, "image_prompt": "scene 1", "description": "First scene"},
        {"scene_id": 2, "image_prompt": "scene 2", "description": "Second scene"},
        {"scene_id": 3, "image_prompt": "scene 3", "description": "Third scene"},
    ]
    
    results = await agent.generate_batch(scenes, sample_character_templates)
    
    assert len(results) == 3
    assert all(isinstance(r, str) and r != "" for r in results)
    assert agent._generate_image_qiniu.await_count == 3


@pytest.mark.asyncio
async def test_generate_batch_with_errors(agent):
    """Test batch generation error handling"""
    # Mock the internal method to always fail
    agent._generate_image_qiniu = AsyncMock(side_effect=Exception("API Error"))
    
    scenes = [
        {"scene_id": i, "image_prompt": f"scene {i}", "description": f"Scene {i}"}
        for i in range(1, 4)
    ]
    
    with pytest.raises(GenerationError):
        await agent.generate_batch(scenes)


@pytest.mark.asyncio
async def test_generate_with_character_consistency(agent, sample_scene, sample_character_templates):
    """Test character consistency in generation"""
    agent._generate_image_qiniu = AsyncMock(return_value=b"fake_image_data")
    agent.task_storage.save_image = AsyncMock(return_value="scene_1_test.png")
    
    result = await agent.generate(sample_scene, sample_character_templates)
    
    assert isinstance(result, str)
    assert Path(result).suffix in ['.png', '.jpg', '.jpeg']


def test_validate_scene_missing_prompt(agent):
    """Test validation for missing image prompt"""
    scene = {"scene_id": 1, "description": "test"}
    
    # This should not raise an exception because there is a description
    agent._validate_scene(scene)


def test_validate_scene_empty_prompt(agent):
    """Test validation for empty image prompt"""
    scene = {
        "scene_id": 1,
        "description": "test",
        "image_prompt": ""
    }
    
    # This should not raise an exception because there is a description
    agent._validate_scene(scene)


def test_validate_scene_no_prompt_no_description(agent):
    """Test validation for missing both image prompt and description"""
    scene = {"scene_id": 1}
    
    with pytest.raises(ValidationError, match="Scene must have 'image_prompt' or 'description'"):
        agent._validate_scene(scene)


def test_validate_scene_empty_prompt_empty_description(agent):
    """Test validation for empty image prompt and description"""
    scene = {
        "scene_id": 1,
        "image_prompt": "",
        "description": ""
    }
    
    with pytest.raises(ValidationError, match="Scene must have 'image_prompt' or 'description'"):
        agent._validate_scene(scene)


def test_validate_scene_valid(agent):
    """Test validation with valid scene"""
    scene = {
        "scene_id": 1,
        "description": "test",
        "image_prompt": "a beautiful landscape"
    }
    
    agent._validate_scene(scene)


def test_build_prompt_without_characters(agent):
    """Test prompt building without characters"""
    scene = {
        "scene_id": 1,
        "image_prompt": "a sunset",
        "description": "beautiful sunset"
    }
    
    prompt = agent._build_prompt(scene, {})
    
    assert "sunset" in prompt.lower()
    assert isinstance(prompt, str)


def test_build_prompt_with_characters(agent, sample_character_templates):
    """Test prompt building with character templates"""
    scene = {
        "scene_id": 1,
        "image_prompt": "a scene with hero",
        "characters": ["小明"],
        "description": "hero in scene"
    }
    
    prompt = agent._build_prompt(scene, sample_character_templates)
    
    assert isinstance(prompt, str)
    assert len(prompt) > 0


@pytest.mark.asyncio
async def test_generate_no_retry_on_success(agent, sample_scene):
    """Test that retry is not triggered on successful generation"""
    agent._generate_image_qiniu = AsyncMock(return_value=b"fake_image_data")
    agent.task_storage.save_image = AsyncMock(return_value="scene_1_test.png")
    
    result = await agent.generate(sample_scene)
    
    agent._generate_image_qiniu.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_with_empty_character_templates(agent, sample_scene):
    """Test generation with empty character templates"""
    agent._generate_image_qiniu = AsyncMock(return_value=b"fake_image_data")
    agent.task_storage.save_image = AsyncMock(return_value="scene_1_test.png")
    
    result = await agent.generate(sample_scene, character_templates={})
    
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_batch_generation_maintains_order(agent):
    """Test that batch generation maintains scene order"""
    agent._generate_image_qiniu = AsyncMock(return_value=b"fake_image_data")
    agent.task_storage.save_image = AsyncMock(side_effect=[
        "scene_1_test.png",
        "scene_2_test.png",
        "scene_3_test.png",
        "scene_4_test.png",
        "scene_5_test.png"
    ])
    
    scenes = [
        {"scene_id": i, "image_prompt": f"prompt {i}", "description": f"scene {i}"}
        for i in range(1, 6)
    ]
    
    results = await agent.generate_batch(scenes)
    
    assert len(results) == 5
    for i, result in enumerate(results, 1):
        assert f"scene_{i}" in result


def test_config_defaults():
    """Test default configuration values"""
    config = ImageGeneratorConfig()
    
    assert config.model == "qwen-image-plus"
    assert config.size == "1024x1024"
    assert config.batch_size > 0
    assert config.retry_attempts >= 0
    assert config.generation_mode == "text2image"


def test_agent_initialization(config):
    """Test agent initialization"""
    agent = ImageGeneratorAgent(
        task_id="test-123",
        config=config
    )
    
    assert agent.task_id == "test-123"
    assert agent.config is not None


@pytest.mark.asyncio
async def test_image2image_generation(agent, sample_scene):
    """Test image to image generation"""
    config = ImageGeneratorConfig(
        qiniu_api_key="test_api_key",
        model="wanx-v3",
        size="1024x1024",
        generation_mode="image2image"
    )
    agent.config = config
    
    agent._generate_image_qiniu_i2i = AsyncMock(return_value=b"fake_image_data")
    agent.task_storage.save_image = AsyncMock(return_value="scene_1_test.png")
    
    reference_image = b"fake_reference_image_data"
    result = await agent.generate(sample_scene, reference_image=reference_image)
    
    assert isinstance(result, str)
    agent._generate_image_qiniu_i2i.assert_awaited_once()


