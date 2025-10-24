import pytest
import asyncio
from pathlib import Path
from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, AIMessage


class FakeLLM(ChatOpenAI):
    """
    Fake LLM for testing that returns predefined responses.
    Eliminates need for mocking LLM calls in tests.
    """
    
    def __init__(self, responses: Dict[str, Any] = None, **kwargs):
        super().__init__(api_key="fake-key", base_url="http://fake-url", **kwargs)
        self.responses = responses or {}
        self.call_count = 0
        self.call_history = []
    
    async def _agenerate(self, messages, **kwargs):
        self.call_count += 1
        self.call_history.append({"messages": messages, "kwargs": kwargs})
        
        response_key = kwargs.get("response_key", "default")
        response_data = self.responses.get(response_key, self.responses.get("default", {}))
        
        if isinstance(response_data, Exception):
            raise response_data
        
        import json
        from langchain_core.outputs import ChatGeneration, ChatResult
        
        content = json.dumps(response_data, ensure_ascii=False)
        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)
        
        return ChatResult(generations=[generation])
    
    def set_response(self, key: str, value: Any):
        """Set a response for a specific key"""
        self.responses[key] = value
    
    def reset(self):
        """Reset call history"""
        self.call_count = 0
        self.call_history = []


@pytest.fixture
def fake_llm():
    """
    Provides a fake LLM instance with default responses.
    Much better than mocking for most test cases.
    """
    default_response = {
        "characters": [
            {
                "name": "测试角色",
                "description": "一个测试角色",
                "appearance": {
                    "gender": "male",
                    "age": 20,
                    "hair": "黑发",
                    "eyes": "棕色眼睛",
                    "clothing": "休闲装",
                    "features": "普通"
                },
                "personality": "友好"
            }
        ],
        "scenes": [
            {
                "scene_id": 1,
                "location": "测试地点",
                "time": "白天",
                "characters": ["测试角色"],
                "description": "测试场景描述",
                "dialogue": [{"character": "测试角色", "text": "测试对话"}],
                "actions": ["测试动作"],
                "atmosphere": "测试氛围"
            }
        ],
        "plot_points": [
            {
                "scene_id": 1,
                "type": "conflict",
                "description": "测试情节点"
            }
        ]
    }
    
    llm = FakeLLM(responses={"default": default_response})
    return llm


@pytest.fixture
def temp_storage_dir(tmp_path):
    """
    Provides a temporary directory for file storage tests.
    Use this instead of mocking LocalStorage.
    """
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return str(storage_dir)


@pytest.fixture
def sample_novel_text():
    """Sample novel text for testing"""
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
def sample_character_data():
    """Sample character data for testing"""
    return {
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
    }


@pytest.fixture
def sample_scene_data():
    """Sample scene data for testing"""
    return {
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
    }


@pytest.fixture
def sample_image_url():
    """Sample image URL for testing"""
    return "https://example.com/test-image.png"


@pytest.fixture
def sample_video_url():
    """Sample video URL for testing"""
    return "https://example.com/test-video.mp4"


@pytest.fixture
def sample_audio_url():
    """Sample audio URL for testing"""
    return "https://example.com/test-audio.mp3"


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the test session.
    Ensures proper async test execution.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
