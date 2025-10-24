import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_openai import ChatOpenAI

from src.agents.novel_parser import (
    NovelParserAgent,
    NovelParserConfig,
    ValidationError,
    ParseError,
    APIError,
)


@pytest.fixture
def mock_llm():
    # Create a mock LLM instance
    llm = MagicMock(spec=ChatOpenAI)
    return llm


@pytest.fixture
def novel_parser_agent(mock_llm):
    config = NovelParserConfig(
        model="gpt-4o-mini",
        max_characters=5,
        max_scenes=10,
        enable_character_enhancement=False,
    )
    # Pass the mock LLM instance to the agent
    return NovelParserAgent(llm=mock_llm, config=config)


@pytest.fixture
def sample_novel_text():
    return """
    第一章 相遇
    
    阳光透过窗户洒进教室,小明坐在座位上认真听课。他是一个16岁的高中生,
    留着短黑发,棕色的眼睛充满了好奇。今天他穿着整洁的校服。
    
    "小明,你能回答这个问题吗?"老师问道。
    
    "好的,老师。"小明站起来,自信地回答。
    
    这时,教室门突然打开,一个女孩走了进来。她叫小红,也是16岁,
    长长的黑发扎成马尾,明亮的眼睛里带着一丝紧张。
    
    第二章 友谊
    
    下课后,小明和小红在操场上相遇。
    
    "你好,我是小明。"他友好地打招呼。
    
    "你好,我是小红。"她微笑着回应。
    
    从那天起,他们成了好朋友。
    """


@pytest.fixture
def sample_llm_response():
    return {
        "characters": [
            {
                "name": "小明",
                "description": "一个16岁的高中生,性格开朗自信",
                "appearance": {
                    "gender": "male",
                    "age": 16,
                    "hair": "短黑发",
                    "eyes": "棕色眼睛",
                    "clothing": "校服",
                    "features": "充满好奇"
                },
                "personality": "自信、友好"
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
                    "features": "有点紧张"
                },
                "personality": "友好、微笑"
            }
        ],
        "scenes": [
            {
                "scene_id": 1,
                "location": "教室",
                "time": "白天",
                "characters": ["小明", "老师"],
                "description": "阳光透过窗户洒进教室",
                "dialogue": [
                    {"character": "老师", "text": "小明,你能回答这个问题吗?"},
                    {"character": "小明", "text": "好的,老师。"}
                ],
                "actions": ["小明站起来回答问题"],
                "atmosphere": "学习氛围"
            },
            {
                "scene_id": 2,
                "location": "操场",
                "time": "下课后",
                "characters": ["小明", "小红"],
                "description": "操场上两人相遇",
                "dialogue": [
                    {"character": "小明", "text": "你好,我是小明。"},
                    {"character": "小红", "text": "你好,我是小红。"}
                ],
                "actions": ["打招呼", "微笑"],
                "atmosphere": "友好"
            }
        ],
        "plot_points": [
            {
                "scene_id": 1,
                "type": "conflict",
                "description": "小红进入教室"
            },
            {
                "scene_id": 2,
                "type": "resolution",
                "description": "两人成为朋友"
            }
        ]
    }


@pytest.mark.asyncio
async def test_parse_simple_mode(novel_parser_agent, sample_novel_text, sample_llm_response):
    with patch.object(novel_parser_agent, '_call_llm_json', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_llm_response
        
        result = await novel_parser_agent.parse(sample_novel_text, mode="simple")
        
        assert "characters" in result
        assert "scenes" in result
        assert "plot_points" in result
        assert len(result["characters"]) == 2
        assert len(result["scenes"]) == 2
        mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_parse_enhanced_mode(novel_parser_agent, sample_novel_text, sample_llm_response):
    with patch.object(novel_parser_agent, '_call_llm_json', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_llm_response
        
        result = await novel_parser_agent.parse(sample_novel_text, mode="enhanced")
        
        assert "characters" in result
        assert "scenes" in result
        assert "plot_points" in result


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
async def test_invalid_mode(novel_parser_agent, sample_novel_text):
    with pytest.raises(ValidationError, match="Invalid mode"):
        await novel_parser_agent.parse(sample_novel_text, mode="invalid")


@pytest.mark.asyncio
async def test_llm_api_error(novel_parser_agent, sample_novel_text):
    with patch.object(novel_parser_agent, '_call_llm_json', new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = APIError("API failed")
        
        with pytest.raises(APIError):
            await novel_parser_agent.parse(sample_novel_text, mode="simple")


@pytest.mark.asyncio
async def test_parse_error_invalid_json(novel_parser_agent, sample_novel_text):
    # Mock the _call_llm_json method to raise a JSONDecodeError
    with patch.object(novel_parser_agent, '_call_llm_json', new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = ParseError("Invalid JSON response: Expecting value: line 1 column 1 (char 0)")
        
        with pytest.raises(ParseError):
            await novel_parser_agent.parse(sample_novel_text, mode="simple")


@pytest.mark.asyncio
async def test_character_enhancement(mock_llm, sample_novel_text, sample_llm_response):
    config = NovelParserConfig(
        model="gpt-4o-mini",
        enable_character_enhancement=True,
    )
    agent = NovelParserAgent(llm=mock_llm, config=config)
    
    visual_desc = {
        "prompt": "anime style, young male student",
        "negative_prompt": "low quality",
        "style_tags": ["anime", "school"]
    }
    
    with patch.object(agent, '_call_llm_json', new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = [sample_llm_response, visual_desc, visual_desc]
        
        result = await agent.parse(sample_novel_text, mode="simple")
        
        assert result["characters"][0].get("visual_description") is not None


@pytest.mark.asyncio
async def test_merge_character_occurrences(novel_parser_agent):
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
    text = "\n\n".join([f"段落{i}" * 100 for i in range(20)])
    chunks = novel_parser_agent._split_text_into_chunks(text, chunk_size=1000)
    
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 1500


@pytest.mark.asyncio
async def test_custom_options(novel_parser_agent, sample_novel_text, sample_llm_response):
    with patch.object(novel_parser_agent, '_call_llm_json', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_llm_response
        
        options = {"max_characters": 3, "max_scenes": 5}
        result = await novel_parser_agent.parse(sample_novel_text, mode="simple", options=options)
        
        assert result is not None


def test_validate_input_empty(novel_parser_agent):
    with pytest.raises(ValidationError):
        novel_parser_agent._validate_input("")


def test_validate_output_missing_keys(novel_parser_agent):
    with pytest.raises(ValidationError, match="Missing required key"):
        novel_parser_agent._validate_output({"characters": []})


def test_validate_output_no_characters(novel_parser_agent):
    with pytest.raises(ValidationError, match="No characters extracted"):
        novel_parser_agent._validate_output({
            "characters": [],
            "scenes": [{"scene_id": 1}],
            "plot_points": []
        })


def test_validate_output_no_scenes(novel_parser_agent):
    with pytest.raises(ValidationError, match="No scenes extracted"):
        novel_parser_agent._validate_output({
            "characters": [{"name": "test"}],
            "scenes": [],
            "plot_points": []
        })