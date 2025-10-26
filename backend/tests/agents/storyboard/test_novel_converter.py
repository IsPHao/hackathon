import pytest

from src.agents.storyboard import (
    StoryboardAgent,
    StoryboardConfig,
    StoryboardResult,
)


@pytest.fixture
def storyboard_agent(fake_llm):
    config = StoryboardConfig(
        max_scenes=10,
        min_scene_duration=3.0,
        max_scene_duration=10.0,
    )
    return StoryboardAgent(llm=fake_llm, config=config)


@pytest.fixture
def sample_novel_parse_result():
    return {
        "characters": [
            {
                "name": "小明",
                "description": "16岁高中生",
                "appearance": {
                    "gender": "male",
                    "age": 16,
                    "age_stage": "少年",
                    "hair": "短黑发",
                    "eyes": "棕色眼睛",
                    "clothing": "校服",
                    "features": "阳光笑容",
                    "body_type": "",
                    "height": "",
                    "skin": ""
                },
                "personality": "开朗自信",
                "role": "主角"
            }
        ],
        "chapters": [
            {
                "chapter_id": 1,
                "title": "第一章：开学",
                "summary": "小明开学第一天",
                "scenes": [
                    {
                        "scene_id": 1,
                        "location": "教室",
                        "time": "早晨",
                        "characters": ["小明"],
                        "description": "阳光洒进教室",
                        "atmosphere": "温暖明亮",
                        "lighting": "soft morning light",
                        "content_type": "dialogue",
                        "narration": "",
                        "speaker": "小明",
                        "dialogue_text": "早上好，大家！",
                        "character_action": "走进教室",
                        "character_appearances": {}
                    },
                    {
                        "scene_id": 2,
                        "location": "教室",
                        "time": "早晨",
                        "characters": ["小明"],
                        "description": "小明坐下",
                        "atmosphere": "温暖",
                        "lighting": "",
                        "content_type": "narration",
                        "narration": "小明找到了自己的座位，坐了下来。",
                        "speaker": "",
                        "dialogue_text": "",
                        "character_action": "坐下",
                        "character_appearances": {}
                    }
                ]
            }
        ],
        "plot_points": []
    }


@pytest.mark.asyncio
async def test_create_from_novel_result(storyboard_agent, sample_novel_parse_result):
    result = await storyboard_agent.create(sample_novel_parse_result)
    
    assert "chapters" in result
    assert len(result["chapters"]) == 1
    assert result["chapters"][0]["chapter_id"] == 1
    assert result["chapters"][0]["title"] == "第一章：开学"
    
    scenes = result["chapters"][0]["scenes"]
    assert len(scenes) == 2
    
    scene1 = scenes[0]
    assert scene1["scene_id"] == 1
    assert scene1["chapter_id"] == 1
    assert scene1["location"] == "教室"
    assert scene1["audio"]["type"] == "dialogue"
    assert scene1["audio"]["speaker"] == "小明"
    assert scene1["audio"]["text"] == "早上好，大家！"
    assert scene1["duration"] > 0
    
    assert len(scene1["characters"]) == 1
    char = scene1["characters"][0]
    assert char["name"] == "小明"
    assert char["gender"] == "male"
    assert char["hair"] == "短黑发"
    
    scene2 = scenes[1]
    assert scene2["audio"]["type"] == "narration"
    assert scene2["audio"]["text"] == "小明找到了自己的座位，坐了下来。"


@pytest.mark.asyncio
async def test_character_appearance_merge(storyboard_agent):
    novel_data = {
        "characters": [
            {
                "name": "小红",
                "description": "15岁女生",
                "appearance": {
                    "gender": "female",
                    "age": 15,
                    "hair": "长黑发",
                    "eyes": "黑色眼睛",
                    "clothing": "校服",
                    "features": "",
                    "body_type": "",
                    "height": "",
                    "skin": "",
                    "age_stage": ""
                },
                "personality": "温柔",
                "role": "配角"
            }
        ],
        "chapters": [
            {
                "chapter_id": 1,
                "title": "测试章节",
                "summary": "",
                "scenes": [
                    {
                        "scene_id": 1,
                        "location": "操场",
                        "time": "下午",
                        "characters": ["小红"],
                        "description": "操场",
                        "atmosphere": "",
                        "lighting": "",
                        "content_type": "dialogue",
                        "narration": "",
                        "speaker": "小红",
                        "dialogue_text": "你好",
                        "character_action": "",
                        "character_appearances": {
                            "小红": {
                                "gender": "female",
                                "age": 15,
                                "hair": "短红发",
                                "eyes": "蓝色眼睛",
                                "clothing": "运动服",
                                "features": "活力",
                                "body_type": "",
                                "height": "",
                                "skin": "",
                                "age_stage": ""
                            }
                        }
                    }
                ]
            }
        ],
        "plot_points": []
    }
    
    result = await storyboard_agent.create(novel_data)
    
    scene = result["chapters"][0]["scenes"][0]
    char = scene["characters"][0]
    
    assert char["hair"] == "短红发"
    assert char["eyes"] == "蓝色眼睛"
    assert char["clothing"] == "运动服"


@pytest.mark.asyncio
async def test_fallback_on_scene_error(storyboard_agent):
    novel_data = {
        "characters": [],
        "chapters": [
            {
                "chapter_id": 1,
                "title": "测试",
                "summary": "",
                "scenes": [
                    {
                        "scene_id": 1,
                        "location": "",
                        "time": "",
                        "characters": [],
                        "description": "",
                        "atmosphere": "",
                        "lighting": "",
                        "content_type": "narration",
                        "narration": "",
                        "speaker": "",
                        "dialogue_text": "",
                        "character_action": "",
                        "character_appearances": {}
                    }
                ]
            }
        ],
        "plot_points": []
    }
    
    result = await storyboard_agent.create(novel_data)
    
    assert len(result["chapters"]) == 1
    assert len(result["chapters"][0]["scenes"]) == 1
    
    scene = result["chapters"][0]["scenes"][0]
    assert scene["scene_id"] == 1
    assert scene["duration"] >= 3.0


@pytest.mark.asyncio
async def test_total_duration_calculation(storyboard_agent, sample_novel_parse_result):
    result = await storyboard_agent.create(sample_novel_parse_result)
    
    assert "total_duration" in result
    assert result["total_duration"] > 0
    assert "total_scenes" in result
    assert result["total_scenes"] == 2
