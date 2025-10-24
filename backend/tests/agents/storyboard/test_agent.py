import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_openai import ChatOpenAI

from src.agents.storyboard import (
    StoryboardAgent,
    StoryboardConfig,
    ValidationError,
    ProcessError,
    APIError,
)


@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=ChatOpenAI)
    return llm


@pytest.fixture
def storyboard_agent(mock_llm):
    config = StoryboardConfig(
        max_scenes=10,
        min_scene_duration=3.0,
        max_scene_duration=10.0,
    )
    return StoryboardAgent(llm=mock_llm, config=config)


@pytest.fixture
def sample_novel_data():
    return {
        "characters": [
            {
                "name": "小明",
                "description": "16岁高中生",
                "appearance": {
                    "gender": "male",
                    "age": 16,
                    "hair": "短黑发",
                    "eyes": "棕色眼睛",
                },
                "personality": "开朗自信"
            }
        ],
        "scenes": [
            {
                "scene_id": 1,
                "location": "教室",
                "time": "早晨",
                "characters": ["小明"],
                "description": "阳光洒进教室",
                "dialogue": [
                    {"character": "小明", "text": "早上好!"}
                ],
                "actions": ["走进教室", "坐下"],
                "atmosphere": "温暖明亮"
            },
            {
                "scene_id": 2,
                "location": "操场",
                "time": "下午",
                "characters": ["小明"],
                "description": "操场上的体育课",
                "dialogue": [],
                "actions": ["跑步", "休息"],
                "atmosphere": "活力"
            }
        ],
        "plot_points": []
    }


@pytest.fixture
def sample_storyboard_response():
    return {
        "scenes": [
            {
                "scene_id": 1,
                "duration": 5.0,
                "shot_type": "medium_shot",
                "camera_angle": "eye_level",
                "camera_movement": "static",
                "transition": "fade",
                "image_prompt": "anime style, classroom scene, morning light",
                "composition": "rule_of_thirds",
                "lighting": "soft morning light",
                "mood": "peaceful"
            },
            {
                "scene_id": 2,
                "duration": 4.5,
                "shot_type": "wide_shot",
                "camera_angle": "high_angle",
                "camera_movement": "pan",
                "transition": "cut",
                "image_prompt": "anime style, outdoor playground, afternoon",
                "composition": "centered",
                "lighting": "natural",
                "mood": "energetic"
            }
        ]
    }


@pytest.mark.asyncio
async def test_create_storyboard(storyboard_agent, sample_novel_data, sample_storyboard_response):
    with patch.object(storyboard_agent, '_call_llm_json', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_storyboard_response
        
        result = await storyboard_agent.create(sample_novel_data)
        
        assert "scenes" in result
        assert len(result["scenes"]) == 2
        assert result["scenes"][0]["scene_id"] == 1
        assert result["scenes"][0]["duration"] > 0
        mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_create_with_options(storyboard_agent, sample_novel_data, sample_storyboard_response):
    with patch.object(storyboard_agent, '_call_llm_json', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = sample_storyboard_response
        
        options = {"max_scenes": 1}
        result = await storyboard_agent.create(sample_novel_data, options=options)
        
        assert len(result["scenes"]) >= 1


@pytest.mark.asyncio
async def test_validate_input_empty(storyboard_agent):
    with pytest.raises(ValidationError, match="cannot be empty"):
        await storyboard_agent.create({})


@pytest.mark.asyncio
async def test_validate_input_no_scenes(storyboard_agent):
    with pytest.raises(ValidationError, match="must contain 'scenes'"):
        await storyboard_agent.create({"characters": []})


@pytest.mark.asyncio
async def test_validate_input_scenes_not_list(storyboard_agent):
    with pytest.raises(ValidationError, match="must be a list"):
        await storyboard_agent.create({"scenes": "not a list"})


@pytest.mark.asyncio
async def test_validate_input_empty_scenes(storyboard_agent):
    with pytest.raises(ValidationError, match="No scenes provided"):
        await storyboard_agent.create({"scenes": []})


@pytest.mark.asyncio
async def test_api_error(storyboard_agent, sample_novel_data):
    with patch.object(storyboard_agent, '_call_llm_json', new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = APIError("API call failed")
        
        with pytest.raises(ProcessError):
            await storyboard_agent.create(sample_novel_data)


def test_calculate_duration(storyboard_agent):
    dialogue = [
        {"character": "小明", "text": "这是一句话"},
        {"character": "小红", "text": "这是另一句话"}
    ]
    actions = ["动作1", "动作2"]
    
    duration = storyboard_agent._calculate_duration(dialogue, actions)
    
    assert duration >= storyboard_agent.config.min_scene_duration
    assert duration <= storyboard_agent.config.max_scene_duration


def test_calculate_duration_min_limit(storyboard_agent):
    duration = storyboard_agent._calculate_duration([], [])
    
    assert duration == storyboard_agent.config.min_scene_duration


def test_calculate_duration_max_limit(storyboard_agent):
    long_dialogue = [{"character": "test", "text": "A" * 1000}]
    many_actions = ["action"] * 100
    
    duration = storyboard_agent._calculate_duration(long_dialogue, many_actions)
    
    assert duration == storyboard_agent.config.max_scene_duration


def test_enhance_image_prompt(storyboard_agent):
    scene = {
        "location": "教室",
        "time": "早晨",
        "atmosphere": "明亮"
    }
    
    enhanced = storyboard_agent._enhance_image_prompt("base prompt", scene)
    
    assert "anime style" in enhanced
    assert "base prompt" in enhanced
    assert "教室" in enhanced
    assert "早晨" in enhanced
    assert "明亮" in enhanced


def test_enhance_scene(storyboard_agent):
    storyboard_scene = {
        "scene_id": 1,
        "shot_type": "medium_shot",
        "image_prompt": "classroom"
    }
    
    original_scene = {
        "scene_id": 1,
        "location": "教室",
        "time": "早晨",
        "dialogue": [{"character": "test", "text": "hello"}],
        "actions": ["action1"]
    }
    
    enhanced = storyboard_agent._enhance_scene(storyboard_scene, original_scene)
    
    assert "duration" in enhanced
    assert enhanced["duration"] > 0
    assert "anime style" in enhanced["image_prompt"]


def test_format_scenes(storyboard_agent):
    scenes = [
        {
            "scene_id": 1,
            "location": "教室",
            "time": "早晨",
            "characters": ["小明"],
            "description": "描述",
            "dialogue": [],
            "actions": [],
            "atmosphere": "明亮"
        }
    ]
    
    formatted = storyboard_agent._format_scenes(scenes)
    
    assert "场景 1" in formatted
    assert "教室" in formatted
    assert "早晨" in formatted


def test_format_characters(storyboard_agent):
    characters = [
        {
            "name": "小明",
            "description": "高中生",
            "appearance": {"hair": "黑发"},
            "personality": "开朗"
        }
    ]
    
    formatted = storyboard_agent._format_characters(characters)
    
    assert "小明" in formatted
    assert "高中生" in formatted
    assert "开朗" in formatted


@pytest.mark.asyncio
async def test_call_llm_json_success(storyboard_agent):
    mock_response = MagicMock()
    mock_response.content = '{"scenes": []}'
    
    with patch.object(storyboard_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = mock_response
        
        result = await storyboard_agent._call_llm_json("test prompt")
        
        assert result == {"scenes": []}
        mock_invoke.assert_called_once()


@pytest.mark.asyncio
async def test_call_llm_json_invalid_json(storyboard_agent):
    mock_response = MagicMock()
    mock_response.content = 'invalid json'
    
    with patch.object(storyboard_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = mock_response
        
        with pytest.raises(ProcessError, match="Invalid JSON response"):
            await storyboard_agent._call_llm_json("test prompt")


@pytest.mark.asyncio
async def test_call_llm_json_api_error(storyboard_agent):
    with patch.object(storyboard_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.side_effect = Exception("API error")
        
        with pytest.raises(APIError, match="Failed to call LLM API"):
            await storyboard_agent._call_llm_json("test prompt")
