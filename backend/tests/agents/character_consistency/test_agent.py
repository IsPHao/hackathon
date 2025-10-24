import pytest
import json

from src.agents.character_consistency import (
    CharacterConsistencyAgent,
    CharacterConsistencyConfig,
    CharacterTemplate,
    ValidationError,
    GenerationError,
)


@pytest.fixture
def agent(fake_llm, fake_character_storage):
    fake_llm.set_response("default", {
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
    })
    
    config = CharacterConsistencyConfig(
        enable_caching=True,
        storage_base_path="test_data",
    )
    return CharacterConsistencyAgent(llm=fake_llm, storage=fake_character_storage, config=config)


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


@pytest.mark.asyncio
async def test_manage_new_characters(agent, sample_characters):
    result = await agent.manage(sample_characters, project_id="test_project")
    
    assert len(result) == 2
    assert "小明" in result
    assert "小红" in result
    assert isinstance(result["小明"], CharacterTemplate)
    assert agent.storage.call_count == 2


@pytest.mark.asyncio
async def test_manage_existing_characters(agent, sample_characters):
    existing_data = {
        "name": "小明",
        "base_prompt": "existing prompt",
        "negative_prompt": "low quality",
        "features": {},
        "reference_image_url": None,
    }
    
    agent.storage.characters["test_project:小明"] = existing_data
    
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
async def test_extract_character_features(agent):
    character_data = {
        "name": "测试",
        "description": "测试角色",
        "appearance": {"gender": "male"},
    }
    
    result = await agent._extract_character_features(character_data)
    
    assert "base_prompt" in result
    assert "features" in result


@pytest.mark.asyncio
async def test_extract_character_features_json_error(fake_llm, fake_character_storage):
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    
    fake_llm._agenerate = lambda *args, **kwargs: ChatResult(
        generations=[ChatGeneration(message=AIMessage(content="invalid json"))]
    )
    
    config = CharacterConsistencyConfig()
    agent = CharacterConsistencyAgent(llm=fake_llm, storage=fake_character_storage, config=config)
    
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
    
    key = f"{project_id}:{character_name}"
    assert agent.storage.reference_images[key] == image_url


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
async def test_caching_enabled(agent, sample_characters):
    await agent.manage([sample_characters[0]], project_id="test_project")
    
    call_count_after_first = agent.storage.call_count
    
    agent.storage.characters["test_project:小明"] = {
        "name": "小明",
        "base_prompt": "cached prompt",
        "negative_prompt": "low quality",
        "features": {},
        "reference_image_url": None,
    }
    
    await agent.manage([sample_characters[0]], project_id="test_project")
    
    assert agent.storage.call_count == call_count_after_first


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
