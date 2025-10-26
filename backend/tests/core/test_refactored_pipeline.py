import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from uuid import uuid4
import sys

sys.modules['backend.src.core.task_manager'] = MagicMock()
sys.modules['backend.src.core.progress_tracker'] = MagicMock()
sys.modules['backend.src.core.error_handler'] = MagicMock()
sys.modules['backend.src.core.context'] = MagicMock()
sys.modules['backend.src.core.interfaces'] = MagicMock()
sys.modules['backend.src.core.config'] = MagicMock()
sys.modules['backend.src.core.llm_factory'] = MagicMock()
sys.modules['backend.src.core.cache'] = MagicMock()

from backend.src.core.pipeline import AnimePipeline


@pytest.fixture
def mock_progress_tracker():
    tracker = Mock()
    tracker.update = AsyncMock()
    tracker.complete = AsyncMock()
    return tracker


@pytest.fixture
def mock_novel_result():
    return MagicMock(
        model_dump=Mock(return_value={
            "characters": [
                {
                    "name": "Alice",
                    "description": "A brave adventurer",
                    "gender": "female",
                    "age": 25
                }
            ],
            "chapters": [
                {
                    "chapter_id": 1,
                    "title": "Chapter 1",
                    "summary": "The beginning",
                    "scenes": [
                        {
                            "scene_id": "1-1",
                            "chapter_id": 1,
                            "description": "A beautiful garden",
                            "location": "Garden",
                            "time": "Morning"
                        }
                    ]
                }
            ]
        })
    )


@pytest.fixture
def mock_storyboard_data():
    return {
        "chapters": [
            {
                "chapter_id": 1,
                "title": "Chapter 1",
                "summary": "The beginning",
                "scenes": [
                    {
                        "scene_id": "1-1",
                        "chapter_id": 1,
                        "description": "A beautiful garden",
                        "location": "Garden",
                        "time": "Morning",
                        "duration": 5.0,
                        "characters": [],
                        "audio": {
                            "type": "narration",
                            "text": "Once upon a time...",
                            "speaker": None
                        },
                        "image": {
                            "prompt": "A beautiful garden scene",
                            "style_tags": ["anime", "vibrant"],
                            "shot_type": "wide shot",
                            "camera_angle": "eye level",
                            "composition": "centered",
                            "lighting": "natural light"
                        }
                    }
                ]
            }
        ],
        "total_duration": 5.0,
        "total_scenes": 1
    }


@pytest.fixture
def mock_render_result():
    return MagicMock(
        total_scenes=1,
        total_duration=5.0,
        chapters=[
            MagicMock(
                chapter_id=1,
                title="Chapter 1",
                scenes=[
                    MagicMock(
                        scene_id="1-1",
                        chapter_id=1,
                        image_path="/path/to/image1.png",
                        audio_path="/path/to/audio1.mp3",
                        duration=5.0
                    )
                ]
            )
        ]
    )


@pytest.fixture
def mock_agents(mock_novel_result, mock_storyboard_data, mock_render_result):
    with patch('backend.src.core.pipeline.ChatOpenAI') as mock_llm:
        with patch('backend.src.core.pipeline.NovelParserAgent') as mock_novel_parser, \
             patch('backend.src.core.pipeline.StoryboardAgent') as mock_storyboard, \
             patch('backend.src.core.pipeline.SceneRenderer') as mock_scene_renderer, \
             patch('backend.src.core.pipeline.SceneComposer') as mock_scene_composer:
            
            mock_novel_parser.return_value.parse = AsyncMock(return_value=mock_novel_result)
            mock_storyboard.return_value.create = AsyncMock(return_value=mock_storyboard_data)
            mock_scene_renderer.return_value.render = AsyncMock(return_value=mock_render_result)
            mock_scene_composer.return_value.execute = AsyncMock(return_value={
                "video_path": "/path/to/final_video.mp4",
                "duration": 5.0,
                "file_size": 1024000,
                "total_scenes": 1,
                "total_chapters": 1
            })
            
            yield {
                "novel_parser": mock_novel_parser,
                "storyboard": mock_storyboard,
                "scene_renderer": mock_scene_renderer,
                "scene_composer": mock_scene_composer
            }


@pytest.mark.asyncio
async def test_refactored_pipeline_execute_success(mock_agents, mock_progress_tracker):
    task_id = uuid4()
    api_key = "test-api-key"
    
    pipeline = AnimePipeline(
        api_key=api_key,
        progress_tracker=mock_progress_tracker,
        task_id=task_id
    )
    
    novel_text = "Once upon a time in a beautiful garden..."
    
    result = await pipeline.execute(novel_text)
    
    assert result["video_path"] == "/path/to/final_video.mp4"
    assert result["duration"] == 5.0
    assert result["scenes_count"] == 1
    
    mock_agents["novel_parser"].return_value.parse.assert_called_once_with(novel_text)
    mock_agents["storyboard"].return_value.create.assert_called_once()
    mock_agents["scene_renderer"].return_value.render.assert_called_once()
    mock_agents["scene_composer"].return_value.execute.assert_called_once()
    
    assert mock_progress_tracker.update.call_count >= 5
    mock_progress_tracker.complete.assert_called_once()


@pytest.mark.asyncio
async def test_refactored_pipeline_with_multiple_scenes(mock_agents, mock_progress_tracker):
    mock_storyboard_data_multi = {
        "chapters": [
            {
                "chapter_id": 1,
                "title": "Chapter 1",
                "summary": "The beginning",
                "scenes": [
                    {
                        "scene_id": "1-1",
                        "chapter_id": 1,
                        "description": "A beautiful garden",
                        "location": "Garden",
                        "time": "Morning",
                        "duration": 5.0,
                        "characters": [],
                        "audio": {"type": "narration", "text": "Scene 1", "speaker": None},
                        "image": {
                            "prompt": "Garden scene",
                            "style_tags": ["anime"],
                            "shot_type": "wide shot",
                            "camera_angle": "eye level",
                            "composition": "centered",
                            "lighting": "natural"
                        }
                    },
                    {
                        "scene_id": "1-2",
                        "chapter_id": 1,
                        "description": "A cozy kitchen",
                        "location": "Kitchen",
                        "time": "Afternoon",
                        "duration": 4.0,
                        "characters": [],
                        "audio": {"type": "narration", "text": "Scene 2", "speaker": None},
                        "image": {
                            "prompt": "Kitchen scene",
                            "style_tags": ["anime"],
                            "shot_type": "medium shot",
                            "camera_angle": "eye level",
                            "composition": "centered",
                            "lighting": "warm"
                        }
                    }
                ]
            }
        ],
        "total_duration": 9.0,
        "total_scenes": 2
    }
    
    mock_render_result_multi = MagicMock(
        total_scenes=2,
        total_duration=9.0,
        chapters=[
            MagicMock(
                chapter_id=1,
                scenes=[
                    MagicMock(scene_id="1-1", image_path="/img1.png", audio_path="/aud1.mp3", duration=5.0),
                    MagicMock(scene_id="1-2", image_path="/img2.png", audio_path="/aud2.mp3", duration=4.0)
                ]
            )
        ]
    )
    
    mock_agents["storyboard"].return_value.create.return_value = mock_storyboard_data_multi
    mock_agents["scene_renderer"].return_value.render.return_value = mock_render_result_multi
    mock_agents["scene_composer"].return_value.execute.return_value = {
        "video_path": "/path/to/video.mp4",
        "duration": 9.0,
        "file_size": 2048000,
        "total_scenes": 2,
        "total_chapters": 1
    }
    
    task_id = uuid4()
    pipeline = AnimePipeline(
        api_key="test-key",
        progress_tracker=mock_progress_tracker,
        task_id=task_id
    )
    
    result = await pipeline.execute("Test novel with multiple scenes")
    
    assert result["scenes_count"] == 2
    assert result["duration"] == 9.0
    assert result["video_path"] == "/path/to/video.mp4"


@pytest.mark.asyncio
async def test_refactored_pipeline_progress_tracking(mock_agents, mock_progress_tracker):
    task_id = uuid4()
    pipeline = AnimePipeline(
        api_key="test-key",
        progress_tracker=mock_progress_tracker,
        task_id=task_id
    )
    
    await pipeline.execute("Test novel")
    
    update_calls = mock_progress_tracker.update.call_args_list
    
    assert any("开始执行" in str(call) for call in update_calls)
    assert any("小说解析" in str(call) for call in update_calls)
    assert any("分镜设计" in str(call) for call in update_calls)
    assert any("场景渲染" in str(call) for call in update_calls)
    assert any("视频合成" in str(call) for call in update_calls)
    
    mock_progress_tracker.complete.assert_called_once()
