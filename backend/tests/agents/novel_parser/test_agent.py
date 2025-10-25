import pytest
import json

from src.agents.novel_parser import (
    NovelParserAgent,
    NovelParserConfig,
    NovelData,
    ValidationError,
    ParseError,
    APIError,
)


@pytest.fixture
def novel_parser_config():
    """Create NovelParserConfig"""
    return NovelParserConfig(
        max_characters=5,
        max_scenes=10,
        enable_character_enhancement=False,
    )


@pytest.fixture
def novel_parser_agent(fake_llm, novel_parser_config, sample_novel_text):
    """Create NovelParserAgent with FakeLLM"""
    return NovelParserAgent(
        novel_text=sample_novel_text,
        config=novel_parser_config,
        llm=fake_llm
    )


@pytest.mark.asyncio
async def test_parse_simple_mode(novel_parser_agent):
    result = await novel_parser_agent.parse(mode="simple")
    
    assert isinstance(result, NovelData)
    assert len(result.characters) >= 1
    assert len(result.scenes) >= 1


@pytest.mark.asyncio
async def test_parse_enhanced_mode(novel_parser_agent):
    result = await novel_parser_agent.parse(mode="enhanced")
    
    assert isinstance(result, NovelData)
    assert len(result.characters) >= 1
    assert len(result.scenes) >= 1


@pytest.mark.asyncio
async def test_input_validation_too_short(fake_llm, novel_parser_config):
    agent = NovelParserAgent(
        novel_text="短文本",
        config=novel_parser_config,
        llm=fake_llm
    )
    with pytest.raises(ValidationError, match="too short"):
        await agent.parse()


@pytest.mark.asyncio
async def test_input_validation_too_long(fake_llm, novel_parser_config):
    long_text = "a" * 100000
    agent = NovelParserAgent(
        novel_text=long_text,
        config=novel_parser_config,
        llm=fake_llm
    )
    with pytest.raises(ValidationError, match="too long"):
        await agent.parse()


@pytest.mark.asyncio
async def test_invalid_mode(novel_parser_agent):
    with pytest.raises(ValidationError, match="Invalid mode"):
        await novel_parser_agent.parse(mode="invalid")


@pytest.mark.asyncio
async def test_llm_api_error(fake_llm, novel_parser_config, sample_novel_text):
    """Test API error handling using FakeLLM with exception response"""
    fake_llm.set_response("default", APIError("API failed"))
    
    agent = NovelParserAgent(
        novel_text=sample_novel_text,
        config=novel_parser_config,
        llm=fake_llm
    )
    
    with pytest.raises(Exception):
        await agent.parse(mode="simple")


@pytest.mark.asyncio
async def test_character_enhancement(fake_llm, sample_novel_text):
    """Test character enhancement"""
    visual_desc_response = {
        "prompt": "anime style, young male student",
        "negative_prompt": "low quality",
        "style_tags": ["anime", "school"]
    }
    
    base_response = {
        "characters": [{
            "name": "小明",
            "description": "高中生",
            "appearance": {
                "gender": "male",
                "age": 16,
                "hair": "短发",
                "eyes": "棕色",
                "clothing": "校服",
                "features": "普通"
            },
            "personality": "开朗"
        }],
        "scenes": [{
            "scene_id": 1,
            "location": "教室",
            "time": "白天",
            "characters": ["小明"],
            "description": "测试",
            "dialogue": [],
            "actions": [],
            "atmosphere": "学习"
        }],
        "plot_points": [{
            "scene_id": 1,
            "type": "conflict",
            "description": "测试"
        }]
    }
    
    fake_llm.set_response("default", base_response)
    
    config = NovelParserConfig(
        enable_character_enhancement=True,
    )
    agent = NovelParserAgent(
        novel_text=sample_novel_text,
        config=config,
        llm=fake_llm
    )
    
    result = await agent.parse(mode="simple")
    
    assert result.characters[0].visual_description is not None


@pytest.mark.asyncio
async def test_merge_character_occurrences(novel_parser_agent):
    """Test character merging logic"""
    occurrences = [
        {
            "name": "小明",
            "description": "高中生",
            "appearance": {"gender": "male", "age": 16, "hair": "短发", "eyes": "black", "clothing": "school", "features": "test"},
            "personality": "开朗"
        },
        {
            "name": "小明",
            "description": "学生会成员",
            "appearance": {"gender": "male", "age": 16, "eyes": "棕色", "clothing": "校服", "hair": "test", "features": "test2"},
            "personality": "负责"
        }
    ]
    
    merged = novel_parser_agent._merge_character_occurrences(occurrences)
    
    assert merged["name"] == "小明"
    assert "高中生" in merged["description"]
    assert "学生会成员" in merged["description"]
    assert merged["appearance"]["hair"] == "短发"
    assert merged["appearance"]["eyes"] == "棕色"


@pytest.mark.asyncio
async def test_split_text_into_chunks(novel_parser_agent):
    """Test text chunking"""
    text = "\n\n".join([f"段落{i}" * 100 for i in range(20)])
    chunks = novel_parser_agent._split_text_into_chunks(text, chunk_size=1000)
    
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 1500


def test_validate_input_empty(novel_parser_agent):
    """Test input validation"""
    with pytest.raises(ValidationError):
        novel_parser_agent._validate_input("")


def test_validate_output_missing_keys(novel_parser_agent):
    """Test output validation"""
    with pytest.raises(ValidationError, match="Missing required key"):
        novel_parser_agent._validate_output({"characters": []})


def test_validate_output_no_characters(novel_parser_agent):
    """Test character validation"""
    with pytest.raises(ValidationError, match="No characters extracted"):
        novel_parser_agent._validate_output({
            "characters": [],
            "scenes": [{"scene_id": 1}],
            "plot_points": []
        })


def test_validate_output_no_scenes(novel_parser_agent):
    """Test scene validation"""
    with pytest.raises(ValidationError, match="No scenes extracted"):
        novel_parser_agent._validate_output({
            "characters": [{"name": "test"}],
            "scenes": [],
            "plot_points": []
        })


@pytest.mark.asyncio
async def test_novel_data_to_dict(novel_parser_agent):
    """Test NovelData to_dict method"""
    result = await novel_parser_agent.parse(mode="simple")
    
    result_dict = result.to_dict()
    assert isinstance(result_dict, dict)
    assert "characters" in result_dict
    assert "scenes" in result_dict
    assert "plot_points" in result_dict


@pytest.mark.asyncio
async def test_novel_data_from_dict(novel_parser_agent):
    """Test NovelData from_dict method"""
    result = await novel_parser_agent.parse(mode="simple")
    result_dict = result.to_dict()
    
    novel_data = NovelData.from_dict(result_dict)
    assert isinstance(novel_data, NovelData)
    assert len(novel_data.characters) == len(result.characters)
