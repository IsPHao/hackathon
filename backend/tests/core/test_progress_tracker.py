import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
import json

from backend.src.core.progress_tracker import ProgressTracker


@pytest.fixture
def mock_redis():
    redis = Mock()
    redis.publish = AsyncMock()
    redis.setex = AsyncMock()
    redis.get = AsyncMock()
    return redis


@pytest.fixture
def progress_tracker(mock_redis):
    return ProgressTracker(redis_client=mock_redis)


@pytest.mark.asyncio
async def test_initialize(progress_tracker, mock_redis):
    project_id = uuid4()
    
    await progress_tracker.initialize(project_id)
    
    assert mock_redis.publish.called
    assert mock_redis.setex.called
    
    call_args = mock_redis.publish.call_args
    channel = call_args[0][0]
    assert channel == f"project:{project_id}:progress"


@pytest.mark.asyncio
async def test_update(progress_tracker, mock_redis):
    project_id = uuid4()
    
    await progress_tracker.update(
        project_id=project_id,
        stage="novel_parsing",
        progress=50,
        message="Processing..."
    )
    
    assert mock_redis.publish.called
    assert mock_redis.setex.called
    
    publish_call_args = mock_redis.publish.call_args[0]
    data = json.loads(publish_call_args[1])
    
    assert data["type"] == "progress"
    assert data["stage"] == "novel_parsing"
    assert data["progress"] == 50
    assert data["message"] == "Processing..."


@pytest.mark.asyncio
async def test_complete(progress_tracker, mock_redis):
    project_id = uuid4()
    video_url = "http://example.com/video.mp4"
    
    await progress_tracker.complete(
        project_id=project_id,
        video_url=video_url
    )
    
    assert mock_redis.publish.called
    
    publish_call_args = mock_redis.publish.call_args[0]
    data = json.loads(publish_call_args[1])
    
    assert data["type"] == "completed"
    assert data["status"] == "completed"
    assert data["progress"] == 100
    assert data["video_url"] == video_url


@pytest.mark.asyncio
async def test_fail(progress_tracker, mock_redis):
    project_id = uuid4()
    error_message = "Test error"
    
    await progress_tracker.fail(
        project_id=project_id,
        error=error_message
    )
    
    assert mock_redis.publish.called
    
    publish_call_args = mock_redis.publish.call_args[0]
    data = json.loads(publish_call_args[1])
    
    assert data["type"] == "error"
    assert data["status"] == "failed"
    assert data["error"] == error_message


@pytest.mark.asyncio
async def test_get_progress(progress_tracker, mock_redis):
    project_id = uuid4()
    expected_data = {
        "project_id": str(project_id),
        "status": "processing",
        "progress": 50
    }
    
    mock_redis.get.return_value = json.dumps(expected_data)
    
    result = await progress_tracker.get_progress(project_id)
    
    assert result == expected_data
    mock_redis.get.assert_called_once_with(f"progress:{project_id}")


@pytest.mark.asyncio
async def test_get_progress_not_found(progress_tracker, mock_redis):
    project_id = uuid4()
    mock_redis.get.return_value = None
    
    result = await progress_tracker.get_progress(project_id)
    
    assert result is None


@pytest.mark.asyncio
async def test_progress_tracker_without_redis():
    tracker = ProgressTracker(redis_client=None)
    project_id = uuid4()
    
    await tracker.initialize(project_id)
    await tracker.update(project_id, "test", 50, "message")
    await tracker.complete(project_id, "http://example.com/video.mp4")
    
    result = await tracker.get_progress(project_id)
    assert result is None
