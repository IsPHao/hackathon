import pytest
import json

from src.agents.novel_parser import (
    NovelParserAgent,
    NovelParserConfig,
    NovelParseResult,
    ValidationError,
    ParseError,
    APIError,
)


@pytest.fixture
def novel_parser_agent(fake_llm):
    """Create NovelParserAgent with FakeLLM instead of mocks"""
    config = NovelParserConfig(
        model="gpt-4o-mini",
        max_characters=5,
        max_scenes=10,
    )
    return NovelParserAgent(llm=fake_llm, config=config)


@pytest.mark.asyncio
async def test_parse_short_text(novel_parser_agent, sample_novel_text):
    """Test parsing short text (auto single-pass mode)"""
    result = await novel_parser_agent.parse(sample_novel_text)
    
    assert isinstance(result, NovelParseResult)
    assert len(result.characters) >= 1
    assert len(result.scenes) >= 1
    assert result.characters[0].name
    assert result.characters[0].appearance.gender


@pytest.mark.asyncio
async def test_parse_long_text(novel_parser_agent, sample_novel_text):
    """Test parsing long text (auto chunked mode)"""
    long_text = sample_novel_text * 20
    result = await novel_parser_agent.parse(long_text)
    
    assert isinstance(result, NovelParseResult)
    assert len(result.characters) >= 1
    assert len(result.scenes) >= 1


@pytest.mark.asyncio
async def test_input_validation_too_short(novel_parser_agent):
    with pytest.raises(ValidationError, match="too short"):
        await novel_parser_agent.parse("短文本")


@pytest.mark.asyncio
async def test_input_validation_too_long(novel_parser_agent):
    long_text = "a" * 100000
    with pytest.raises(ValidationError, match="too long"):
        await novel_parser_agent.parse(long_text)


@pytest.mark.asyncio
async def test_auto_chunk_threshold(fake_llm):
    """Test automatic chunking based on threshold"""
    config = NovelParserConfig(
        model="gpt-4o-mini",
        enable_character_enhancement=False,
        auto_chunk_threshold=1000,
    )
    agent = NovelParserAgent(llm=fake_llm, config=config)
    
    short_text = "短文本" * 50
    long_text = "长文本" * 500
    
    assert len(short_text) < 1000
    assert len(long_text) > 1000


@pytest.mark.asyncio
async def test_llm_api_error(fake_llm, sample_novel_text):
    """Test API error handling using FakeLLM with exception response"""
    fake_llm.set_response("default", APIError("API failed"))
    
    config = NovelParserConfig(
        model="gpt-4o-mini",
    )
    agent = NovelParserAgent(llm=fake_llm, config=config)
    
    with pytest.raises(Exception):
        await agent.parse(sample_novel_text)


@pytest.mark.asyncio
async def test_merge_character_occurrences(novel_parser_agent):
    """Test character merging logic without mocks"""
    occurrences = [
        {
            "name": "小明",
            "description": "高中生",
            "appearance": {"gender": "male", "age": 16, "hair": "短发"},
            "personality": "开朗"
        },
        {
            "name": "小明",
            "description": "学生会成员",
            "appearance": {"gender": "male", "eyes": "棕色", "clothing": "校服"},
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
    """Test text chunking without mocks"""
    text = "\n\n".join([f"段落{i}" * 100 for i in range(20)])
    chunks = novel_parser_agent._split_text_into_chunks(text)
    
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 5000


@pytest.mark.asyncio
async def test_custom_options(novel_parser_agent, sample_novel_text):
    """Test custom options without mocks"""
    options = {"max_characters": 3, "max_scenes": 5}
    result = await novel_parser_agent.parse(sample_novel_text, options=options)
    
    assert result is not None


def test_validate_input_empty(novel_parser_agent):
    """Test input validation without mocks"""
    with pytest.raises(ValidationError):
        novel_parser_agent._validate_input("")


def test_validate_output_missing_keys(novel_parser_agent):
    """Test output validation without mocks"""
    result = NovelParseResult(characters=[], scenes=[], plot_points=[])
    with pytest.raises(ValidationError, match="No characters extracted"):
        novel_parser_agent._validate_output_model(result)


def test_validate_output_no_characters(novel_parser_agent):
    """Test character validation without mocks"""
    from src.agents.novel_parser.models import SceneInfo
    result = NovelParseResult(
        characters=[],
        scenes=[SceneInfo(scene_id=1)],
        plot_points=[]
    )
    with pytest.raises(ValidationError, match="No characters extracted"):
        novel_parser_agent._validate_output_model(result)


def test_validate_output_no_scenes(novel_parser_agent):
    """Test scene validation without mocks"""
    from src.agents.novel_parser.models import CharacterInfo
    result = NovelParseResult(
        characters=[CharacterInfo(name="test")],
        scenes=[],
        plot_points=[]
    )
    with pytest.raises(ValidationError, match="No scenes extracted"):
        novel_parser_agent._validate_output_model(result)