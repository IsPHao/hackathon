import pytest
from pathlib import Path

from src.agents.image_generator import (
    ImageGeneratorAgent,
    ImageGeneratorConfig,
    ValidationError,
    GenerationError,
)


@pytest.fixture
def agent(fake_openai_client):
    """Create ImageGeneratorAgent with fake OpenAI client"""
    config = ImageGeneratorConfig(
        model="dall-e-3",
        size="1024x1024",
        batch_size=3,
        retry_attempts=2,
    )
    return ImageGeneratorAgent(
        openai_client=fake_openai_client,
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
async def test_generate_success(agent, fake_openai_client, sample_scene, sample_character_templates):
    """Test successful image generation without mocks"""
    result = await agent.generate(sample_scene, sample_character_templates)
    
    assert isinstance(result, str)
    assert "scene_1" in result
    assert fake_openai_client.call_count > 0


@pytest.mark.asyncio
async def test_generate_with_retry(agent, fake_openai_client, sample_scene):
    """Test retry mechanism using fake client failure simulation"""
    fake_openai_client.set_failure(count=3)
    
    with pytest.raises(GenerationError, match="Failed to generate image after"):
        await agent.generate(sample_scene)


@pytest.mark.asyncio
async def test_generate_batch(agent, fake_openai_client, sample_character_templates):
    """Test batch generation without mocks"""
    scenes = [
        {"scene_id": 1, "image_prompt": "scene 1", "description": "First scene"},
        {"scene_id": 2, "image_prompt": "scene 2", "description": "Second scene"},
        {"scene_id": 3, "image_prompt": "scene 3", "description": "Third scene"},
    ]
    
    results = await agent.generate_batch(scenes, sample_character_templates)
    
    assert len(results) == 3
    assert all(isinstance(r, str) and r != "" for r in results)
    assert fake_openai_client.call_count == 3


@pytest.mark.asyncio
async def test_generate_batch_with_errors(agent, fake_openai_client):
    """Test batch generation error handling"""
    scenes = [
        {"scene_id": i, "image_prompt": f"scene {i}", "description": f"Scene {i}"}
        for i in range(1, 4)
    ]
    
    fake_openai_client.set_failure(count=99)
    
    with pytest.raises(GenerationError):
        await agent.generate_batch(scenes)


@pytest.mark.asyncio
async def test_generate_with_character_consistency(agent, sample_scene, sample_character_templates):
    """Test character consistency in generation"""
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
async def test_generate_no_retry_on_success(agent, fake_openai_client, sample_scene):
    """Test that retry is not triggered on successful generation"""
    result = await agent.generate(sample_scene)
    
    assert fake_openai_client.call_count == 1


@pytest.mark.asyncio
async def test_generate_with_empty_character_templates(agent, sample_scene):
    """Test generation with empty character templates"""
    result = await agent.generate(sample_scene, character_templates={})
    
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_batch_generation_maintains_order(agent, fake_openai_client):
    """Test that batch generation maintains scene order"""
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
    
    assert config.model == "dall-e-3"
    assert config.size == "1024x1024"
    assert config.batch_size > 0
    assert config.retry_attempts >= 0


def test_agent_initialization(fake_openai_client):
    """Test agent initialization"""
    agent = ImageGeneratorAgent(
        openai_client=fake_openai_client,
        task_id="test-123"
    )
    
    assert agent.task_id == "test-123"
    assert agent.config is not None
    assert agent.client == fake_openai_client