import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from backend.src.core.pipeline import AnimePipeline
from backend.src.core.progress_tracker import ProgressTracker
from backend.src.core.error_handler import ErrorHandler
from backend.src.core.exceptions import PipelineError
from backend.src.core.config import CoreSettings


@pytest.fixture
def mock_agents():
    return {
        "novel_parser": AsyncMock(),
        "storyboard": AsyncMock(),
        "character_consistency": AsyncMock(),
        "image_generator": AsyncMock(),
        "voice_synthesizer": AsyncMock(),
        "video_composer": AsyncMock(),
    }


@pytest.fixture
def mock_progress_tracker():
    tracker = Mock(spec=ProgressTracker)
    tracker.initialize = AsyncMock()
    tracker.update = AsyncMock()
    tracker.complete = AsyncMock()
    tracker.fail = AsyncMock()
    return tracker


@pytest.fixture
def mock_error_handler():
    handler = Mock(spec=ErrorHandler)
    handler.handle = AsyncMock()
    return handler


@pytest.fixture
def pipeline(mock_agents, mock_progress_tracker, mock_error_handler):
    return AnimePipeline(
        novel_parser=mock_agents["novel_parser"],
        storyboard=mock_agents["storyboard"],
        character_consistency=mock_agents["character_consistency"],
        image_generator=mock_agents["image_generator"],
        voice_synthesizer=mock_agents["voice_synthesizer"],
        video_composer=mock_agents["video_composer"],
        progress_tracker=mock_progress_tracker,
        error_handler=mock_error_handler,
    )


@pytest.mark.asyncio
async def test_pipeline_execute_success(pipeline, mock_agents, mock_progress_tracker):
    project_id = uuid4()
    novel_text = "Test novel text"
    
    mock_agents["novel_parser"].parse.return_value = {
        "characters": [{"name": "Alice"}],
        "scenes": [{"scene_id": 1}],
        "plot_points": []
    }
    mock_agents["storyboard"].create.return_value = {
        "scenes": [{"scene_id": 1}]
    }
    mock_agents["character_consistency"].manage.return_value = {
        "characters": [{"name": "Alice"}]
    }
    mock_agents["image_generator"].generate.return_value = "http://example.com/image1.jpg"
    mock_agents["voice_synthesizer"].synthesize.return_value = "http://example.com/audio1.mp3"
    mock_agents["video_composer"].compose.return_value = {
        "url": "http://example.com/video.mp4",
        "thumbnail_url": "http://example.com/thumb.jpg",
        "duration": 120.0
    }
    
    result = await pipeline.execute(project_id, novel_text)
    
    assert result["video_url"] == "http://example.com/video.mp4"
    assert result["thumbnail_url"] == "http://example.com/thumb.jpg"
    assert result["duration"] == 120.0
    assert result["scenes_count"] == 1
    
    mock_agents["novel_parser"].parse.assert_called_once_with(novel_text)
    mock_agents["storyboard"].create.assert_called_once()
    mock_agents["character_consistency"].manage.assert_called_once()
    mock_agents["image_generator"].generate.assert_called_once()
    mock_agents["voice_synthesizer"].synthesize.assert_called_once()
    mock_agents["video_composer"].compose.assert_called_once()
    
    mock_progress_tracker.initialize.assert_called_once_with(project_id)
    mock_progress_tracker.complete.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_execute_with_retry(pipeline, mock_agents):
    project_id = uuid4()
    novel_text = "Test novel text"
    
    mock_agents["novel_parser"].parse.side_effect = [
        Exception("API Error"),
        Exception("API Error"),
        {
            "characters": [{"name": "Alice"}],
            "scenes": [{"scene_id": 1}],
            "plot_points": []
        }
    ]
    mock_agents["storyboard"].create.return_value = {"scenes": []}
    mock_agents["character_consistency"].manage.return_value = {"characters": []}
    mock_agents["video_composer"].compose.return_value = {
        "url": "http://example.com/video.mp4"
    }
    
    result = await pipeline.execute(project_id, novel_text)
    
    assert result["video_url"] == "http://example.com/video.mp4"
    assert mock_agents["novel_parser"].parse.call_count == 3


@pytest.mark.asyncio
async def test_pipeline_execute_failure(pipeline, mock_agents, mock_error_handler, mock_progress_tracker):
    project_id = uuid4()
    novel_text = "Test novel text"
    
    mock_agents["novel_parser"].parse.side_effect = Exception("Fatal Error")
    
    with pytest.raises(PipelineError):
        await pipeline.execute(project_id, novel_text)
    
    mock_error_handler.handle.assert_called_once()
    mock_progress_tracker.fail.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_execute_with_multiple_scenes(pipeline, mock_agents, mock_progress_tracker):
    project_id = uuid4()
    novel_text = "Test novel text"
    
    mock_agents["novel_parser"].parse.return_value = {
        "characters": [{"name": "Alice"}, {"name": "Bob"}],
        "scenes": [{"scene_id": 1}, {"scene_id": 2}, {"scene_id": 3}],
        "plot_points": []
    }
    mock_agents["storyboard"].create.return_value = {
        "scenes": [{"scene_id": 1}, {"scene_id": 2}, {"scene_id": 3}]
    }
    mock_agents["character_consistency"].manage.return_value = {
        "characters": [{"name": "Alice"}, {"name": "Bob"}]
    }
    mock_agents["image_generator"].generate.side_effect = [
        "http://example.com/image1.jpg",
        "http://example.com/image2.jpg",
        "http://example.com/image3.jpg"
    ]
    mock_agents["voice_synthesizer"].synthesize.side_effect = [
        "http://example.com/audio1.mp3",
        "http://example.com/audio2.mp3",
        "http://example.com/audio3.mp3"
    ]
    mock_agents["video_composer"].compose.return_value = {
        "url": "http://example.com/video.mp4",
        "duration": 360.0
    }
    
    result = await pipeline.execute(project_id, novel_text)
    
    assert result["scenes_count"] == 3
    assert mock_agents["image_generator"].generate.call_count == 3
    assert mock_agents["voice_synthesizer"].synthesize.call_count == 3


@pytest.mark.asyncio
async def test_execute_with_retry_exhausted(pipeline):
    async def failing_func():
        raise Exception("Always fails")
    
    with pytest.raises(Exception, match="Always fails"):
        await pipeline._execute_with_retry(failing_func, max_retries=2)
