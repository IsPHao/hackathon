import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from backend.src.agents.novel_parser import (
    NovelParserAgent,
    NovelParserConfig,
    ValidationError,
    ParseError,
    APIError,
)


@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    return client


@pytest.fixture
def mock_redis_client():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    return redis


@pytest.fixture
def novel_parser_agent(mock_llm_client):
    config = NovelParserConfig(
        model="gpt-4o-mini",
        max_characters=5,
        max_scenes=10,
        enable_character_enhancement=False,
        enable_caching=False,
    )
    return NovelParserAgent(llm_client=mock_llm_client, config=config)


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
    return json.dumps({
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
                "actions": ["小明站起来回答"],
                "atmosphere": "安静、认真"
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
                "atmosphere": "友好、轻松"
            }
        ],
        "plot_points": [
            {
                "scene_id": 1,
                "type": "introduction",
                "description": "小明和小红的初次见面"
            }
        ]
    })


@pytest.mark.asyncio
async def test_parse_simple_mode(novel_parser_agent, mock_llm_client, sample_novel_text, sample_llm_response):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = sample_llm_response
    mock_llm_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    result = await novel_parser_agent.parse(sample_novel_text, mode="simple")
    
    assert "characters" in result
    assert "scenes" in result
    assert "plot_points" in result
    assert len(result["characters"]) == 2
    assert len(result["scenes"]) == 2
    assert result["characters"][0]["name"] == "小明"


@pytest.mark.asyncio
async def test_parse_enhanced_mode(novel_parser_agent, mock_llm_client, sample_novel_text, sample_llm_response):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = sample_llm_response
    mock_llm_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    result = await novel_parser_agent.parse(sample_novel_text, mode="enhanced")
    
    assert "characters" in result
    assert "scenes" in result
    assert "plot_points" in result


@pytest.mark.asyncio
async def test_validation_error_short_text(novel_parser_agent):
    short_text = "Too short"
    
    with pytest.raises(ValidationError, match="Novel text too short"):
        await novel_parser_agent.parse(short_text)


@pytest.mark.asyncio
async def test_validation_error_long_text(novel_parser_agent):
    long_text = "a" * 60000
    
    with pytest.raises(ValidationError, match="Novel text too long"):
        await novel_parser_agent.parse(long_text)


@pytest.mark.asyncio
async def test_invalid_mode(novel_parser_agent, sample_novel_text):
    with pytest.raises(ValidationError, match="Invalid mode"):
        await novel_parser_agent.parse(sample_novel_text, mode="invalid")


@pytest.mark.asyncio
async def test_parse_error_invalid_json(novel_parser_agent, mock_llm_client, sample_novel_text):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "invalid json"
    mock_llm_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    with pytest.raises(ParseError):
        await novel_parser_agent.parse(sample_novel_text, mode="simple")


@pytest.mark.asyncio
async def test_api_error(novel_parser_agent, mock_llm_client, sample_novel_text):
    mock_llm_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
    
    with pytest.raises(APIError):
        await novel_parser_agent.parse(sample_novel_text, mode="simple")


@pytest.mark.asyncio
async def test_caching_enabled(mock_llm_client, mock_redis_client, sample_novel_text, sample_llm_response):
    config = NovelParserConfig(enable_caching=True, enable_character_enhancement=False)
    agent = NovelParserAgent(llm_client=mock_llm_client, config=config, redis_client=mock_redis_client)
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = sample_llm_response
    mock_llm_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    result = await agent.parse(sample_novel_text, mode="simple")
    
    mock_redis_client.get.assert_called_once()
    mock_redis_client.setex.assert_called_once()


@pytest.mark.asyncio
async def test_cache_hit(mock_llm_client, mock_redis_client, sample_novel_text, sample_llm_response):
    config = NovelParserConfig(enable_caching=True, enable_character_enhancement=False)
    agent = NovelParserAgent(llm_client=mock_llm_client, config=config, redis_client=mock_redis_client)
    
    cached_data = json.loads(sample_llm_response)
    mock_redis_client.get = AsyncMock(return_value=json.dumps(cached_data))
    
    result = await agent.parse(sample_novel_text, mode="simple")
    
    assert result == cached_data
    mock_llm_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_character_enhancement(mock_llm_client, sample_novel_text, sample_llm_response):
    config = NovelParserConfig(enable_character_enhancement=True, enable_caching=False)
    agent = NovelParserAgent(llm_client=mock_llm_client, config=config)
    
    visual_desc = json.dumps({
        "prompt": "anime style, 16 year old male student",
        "negative_prompt": "low quality",
        "style_tags": ["anime", "student"]
    })
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_llm_client.chat.completions.create = AsyncMock(
        side_effect=[
            MagicMock(choices=[MagicMock(message=MagicMock(content=sample_llm_response))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content=visual_desc))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content=visual_desc))]),
        ]
    )
    
    result = await agent.parse(sample_novel_text, mode="simple")
    
    assert "visual_description" in result["characters"][0]
    assert "prompt" in result["characters"][0]["visual_description"]


def test_split_text_into_chunks(novel_parser_agent):
    text = "para1\n\npara2\n\npara3\n\npara4"
    chunks = novel_parser_agent._split_text_into_chunks(text, chunk_size=15)
    
    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk) <= 30


def test_merge_character_occurrences(novel_parser_agent):
    occurrences = [
        {
            "name": "小明",
            "description": "高中生",
            "appearance": {"gender": "male", "age": 16, "hair": "短发"},
            "personality": "开朗"
        },
        {
            "name": "小明",
            "description": "篮球运动员",
            "appearance": {"hair": "短黑发", "eyes": "棕色"},
            "personality": "勇敢"
        }
    ]
    
    merged = novel_parser_agent._merge_character_occurrences(occurrences)
    
    assert merged["name"] == "小明"
    assert "高中生" in merged["description"]
    assert "篮球运动员" in merged["description"]
    assert merged["appearance"]["hair"] == "短黑发"
    assert merged["appearance"]["eyes"] == "棕色"


@pytest.mark.asyncio
async def test_custom_options(novel_parser_agent, mock_llm_client, sample_novel_text, sample_llm_response):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = sample_llm_response
    mock_llm_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    options = {"max_characters": 3, "max_scenes": 5}
    result = await novel_parser_agent.parse(sample_novel_text, mode="simple", options=options)
    
    assert len(result["characters"]) <= 3
    assert len(result["scenes"]) <= 5


def test_config_defaults():
    config = NovelParserConfig()
    
    assert config.model == "gpt-4o-mini"
    assert config.max_characters == 10
    assert config.max_scenes == 30
    assert config.temperature == 0.3
    assert config.enable_character_enhancement is True
    assert config.enable_caching is True


def test_config_custom_values():
    config = NovelParserConfig(
        model="gpt-4o",
        max_characters=5,
        temperature=0.5,
        enable_caching=False
    )
    
    assert config.model == "gpt-4o"
    assert config.max_characters == 5
    assert config.temperature == 0.5
    assert config.enable_caching is False
