import pytest
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, AIMessage
from pydantic import BaseModel, Field


class FakeLLM(ChatOpenAI, BaseModel):
    """
    Fake LLM for testing that returns predefined responses.
    Eliminates need for mocking LLM calls in tests.
    """
    
    responses: Dict[str, Any] = Field(default_factory=dict)
    call_count: int = Field(default=0)
    call_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    def __init__(self, responses: Optional[Dict[str, Any]] = None, **kwargs):
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
        "chapters": [
            {
                "chapter_id": 1,
                "title": "测试章节",
                "summary": "这是一个测试章节",
                "scenes": [
                    {
                        "scene_id": 1,
                        "location": "测试地点",
                        "time": "白天",
                        "characters": ["测试角色"],
                        "description": "测试场景描述",
                        "narration": "测试旁白",
                        "dialogue": [{"character": "测试角色", "text": "测试对话"}],
                        "actions": ["测试动作"],
                        "atmosphere": "测试氛围"
                    }
                ]
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


class FakeOpenAIClient:
    """
    Fake OpenAI client for testing image generation.
    Eliminates need for mocking OpenAI API calls.
    """
    
    def __init__(self):
        self.call_count = 0
        self.call_history = []
        self.should_fail = False
        self.failure_count = 0
        self._current_failures = 0
        
        self.images = self
    
    async def generate(self, **kwargs):
        """Simulate OpenAI image generation"""
        self.call_count += 1
        self.call_history.append(kwargs)
        
        if self.should_fail and self._current_failures < self.failure_count:
            self._current_failures += 1
            raise Exception("API Error")
        
        self._current_failures = 0
        
        class FakeImageData:
            url = "/tmp/test_image.png"  # Use a local file path instead of a remote URL
        
        class FakeResponse:
            data = [FakeImageData()]
        
        # Create a dummy image file for testing
        import os
        if not os.path.exists("/tmp/test_image.png"):
            with open("/tmp/test_image.png", "wb") as f:
                f.write(b"fake image data for testing")
        
        return FakeResponse()
    
    def set_failure(self, count: int = 1):
        """Set number of times to fail before succeeding"""
        self.should_fail = True
        self.failure_count = count
        self._current_failures = 0
    
    def reset(self):
        """Reset client state"""
        self.call_count = 0
        self.call_history = []
        self.should_fail = False
        self.failure_count = 0
        self._current_failures = 0


@pytest.fixture
def fake_openai_client():
    """Provides a fake OpenAI client for testing"""
    return FakeOpenAIClient()


class FakeStorage:
    """
    Fake storage backend for testing.
    Simulates file storage without actual I/O or mocking.
    """
    
    def __init__(self, base_path: str = "/tmp/fake-storage"):
        self.base_path = Path(base_path)
        self.saved_files = {}
        self.call_count = 0
    
    async def save(self, data: bytes, filename: str) -> str:
        """Simulate saving data to storage"""
        self.call_count += 1
        url = f"https://fake-storage.example.com/{filename}"
        self.saved_files[filename] = {
            "data": data,
            "url": url,
            "size": len(data)
        }
        return url
    
    async def save_file(self, file_path: str, filename: str) -> str:
        """Simulate saving file to storage"""
        self.call_count += 1
        file_path_obj = Path(file_path)
        if file_path_obj.exists():
            data = file_path_obj.read_bytes()
            return await self.save(data, filename)
        
        url = f"https://fake-storage.example.com/{filename}"
        self.saved_files[filename] = {
            "data": b"fake-data",
            "url": url,
            "size": 100
        }
        return url
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False
    
    def reset(self):
        """Reset storage state"""
        self.saved_files = {}
        self.call_count = 0


@pytest.fixture
def fake_storage():
    """Provides a fake storage backend for testing"""
    return FakeStorage()


@pytest.fixture
def sample_storyboard():
    """Sample storyboard data for video composition"""
    return {
        "scenes": [
            {
                "scene_id": 1,
                "description": "Opening scene",
                "duration": 3.0,
                "location": "教室",
                "characters": ["小明"]
            },
            {
                "scene_id": 2,
                "description": "Second scene",
                "duration": 3.0,
                "location": "操场",
                "characters": ["小明", "小红"]
            }
        ]
    }


@pytest.fixture
def sample_character_templates():
    """Sample character templates for image generation"""
    return {
        "小明": {
            "name": "小明",
            "base_prompt": "anime style, young male student",
            "visual_description": "16岁男生，短黑发，校服"
        },
        "小红": {
            "name": "小红",
            "base_prompt": "anime style, young female student",
            "visual_description": "16岁女生，长黑发，校服"
        }
    }


class FakeAudioClient:
    """
    Fake OpenAI audio client for testing voice synthesis.
    Eliminates need for mocking OpenAI TTS API calls.
    """
    
    def __init__(self):
        self.call_count = 0
        self.call_history = []
        self.should_fail = False
        
        self.audio = self
        self.speech = self
    
    async def create(self, **kwargs):
        """Simulate OpenAI TTS API call"""
        self.call_count += 1
        self.call_history.append(kwargs)
        
        if self.should_fail:
            raise Exception("API Error")
        
        class FakeAudioResponse:
            content = b"fake audio data"
        
        return FakeAudioResponse()
    
    def set_failure(self):
        """Make next call fail"""
        self.should_fail = True
    
    def reset(self):
        """Reset client state"""
        self.call_count = 0
        self.call_history = []
        self.should_fail = False


@pytest.fixture
def fake_audio_client():
    """Provides a fake audio client for testing"""
    return FakeAudioClient()


class FakeCharacterStorage:
    """
    Fake character storage for testing.
    Simulates character template storage without actual I/O.
    """
    
    def __init__(self):
        self.characters = {}
        self.reference_images = {}
        self.call_count = 0
    
    async def load_character(self, project_id: str, character_name: str):
        """Simulate loading character data"""
        key = f"{project_id}:{character_name}"
        return self.characters.get(key)
    
    async def save_character(self, project_id: str, character_name: str, data: dict):
        """Simulate saving character data"""
        self.call_count += 1
        key = f"{project_id}:{character_name}"
        self.characters[key] = data
    
    async def character_exists(self, project_id: str, character_name: str) -> bool:
        """Check if character exists in storage"""
        key = f"{project_id}:{character_name}"
        return key in self.characters
    
    async def save_reference_image(self, project_id: str, character_name: str, image_url: str):
        """Simulate saving reference image"""
        self.call_count += 1
        key = f"{project_id}:{character_name}"
        self.reference_images[key] = image_url
    
    def reset(self):
        """Reset storage state"""
        self.characters = {}
        self.reference_images = {}
        self.call_count = 0


@pytest.fixture
def fake_character_storage():
    """Provides a fake character storage for testing"""
    return FakeCharacterStorage()
