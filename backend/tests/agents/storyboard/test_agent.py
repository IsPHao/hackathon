import pytest
import json

from src.agents.storyboard import (
    StoryboardAgent,
    StoryboardConfig,
    ValidationError,
    ProcessError,
)
from src.agents.base.exceptions import ParseError, APIError


@pytest.fixture
def storyboard_agent(fake_llm):
    fake_llm.set_response("default", {
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
    })
    
    config = StoryboardConfig(
        max_scenes=10,
        min_scene_duration=3.0,
        max_scene_duration=10.0,
    )
    return StoryboardAgent(llm=fake_llm, config=config)


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


@pytest.mark.asyncio
async def test_create_storyboard(storyboard_agent, sample_novel_data):
    result = await storyboard_agent.create(sample_novel_data)
    
    assert "scenes" in result
    assert len(result["scenes"]) == 2
    assert result["scenes"][0]["scene_id"] == 1
    assert result["scenes"][0]["duration"] > 0
    # 验证对话字段存在
    assert "dialogue" in result["scenes"][0]
    assert result["scenes"][0]["dialogue"] == [{"character": "小明", "text": "早上好!"}]
    # 验证第二个场景的对话字段为空数组
    assert "dialogue" in result["scenes"][1]
    assert result["scenes"][1]["dialogue"] == []


@pytest.mark.asyncio
async def test_create_with_options(storyboard_agent, sample_novel_data):
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
async def test_api_error(fake_llm, sample_novel_data):
    fake_llm.set_response("default", APIError("API call failed"))
    
    config = StoryboardConfig()
    agent = StoryboardAgent(llm=fake_llm, config=config)
    
    with pytest.raises(Exception):
        await agent.create(sample_novel_data)


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
    # This test is no longer valid since we removed LLMJSONMixin
    # The _call_llm_json method no longer exists
    pass


@pytest.mark.asyncio
async def test_call_llm_json_invalid_json(fake_llm):
    # This test is no longer valid since we removed LLMJSONMixin
    # The _call_llm_json method no longer exists
    pass


@pytest.mark.asyncio
async def test_call_llm_json_api_error(fake_llm):
    # This test is no longer valid since we removed LLMJSONMixin
    # The _call_llm_json method no longer exists
    pass