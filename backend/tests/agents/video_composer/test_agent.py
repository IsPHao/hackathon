import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import shutil

from src.agents.video_composer import (
    VideoComposerAgent,
    VideoComposerConfig,
    ValidationError,
    CompositionError,
    DownloadError,
)
from src.agents.base import LocalStorage


@pytest.fixture
def temp_dir():
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def mock_storage():
    storage = AsyncMock(spec=LocalStorage)
    storage.save = AsyncMock(return_value="https://example.com/video.mp4")
    storage.save_file = AsyncMock(return_value="https://example.com/video.mp4")
    return storage


@pytest.fixture
def agent(mock_storage):
    config = VideoComposerConfig(
        timeout=60,
    )
    return VideoComposerAgent(
        task_id="test-task-123",
        config=config,
        storage=mock_storage
    )


@pytest.fixture
def sample_storyboard():
    return {
        "scenes": [
            {
                "scene_id": 1,
                "description": "Scene 1",
                "duration": 3.0,
            },
            {
                "scene_id": 2,
                "description": "Scene 2",
                "duration": 3.0,
            },
        ]
    }


@pytest.mark.asyncio
async def test_compose_success(agent, sample_storyboard, temp_dir):
    images = [
        str(Path(temp_dir) / "image1.png"),
        str(Path(temp_dir) / "image2.png"),
    ]
    audios = [
        str(Path(temp_dir) / "audio1.mp3"),
        str(Path(temp_dir) / "audio2.mp3"),
    ]
    
    for img in images:
        Path(img).write_bytes(b"fake image")
    for audio in audios:
        Path(audio).write_bytes(b"fake audio")
    
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_process
        
        result = await agent.compose(images, audios, sample_storyboard)
        
        assert result["url"] == "https://example.com/video.mp4"
        assert "duration" in result
        assert "file_size" in result
        assert "thumbnail_url" in result


@pytest.mark.asyncio
async def test_compose_mismatched_images(agent, sample_storyboard):
    images = ["image1.png"]
    audios = ["audio1.mp3", "audio2.mp3"]
    
    with pytest.raises(ValidationError, match="Number of images"):
        await agent.compose(images, audios, sample_storyboard)


@pytest.mark.asyncio
async def test_compose_mismatched_audios(agent, sample_storyboard):
    images = ["image1.png", "image2.png"]
    audios = ["audio1.mp3"]
    
    with pytest.raises(ValidationError, match="Number of audios"):
        await agent.compose(images, audios, sample_storyboard)


@pytest.mark.asyncio
async def test_download_resource_local_file(agent, temp_dir):
    local_file = Path(temp_dir) / "local.png"
    local_file.write_bytes(b"local data")
    
    result = await agent._download_resource(str(local_file), "images", 0)
    
    assert result == str(local_file)


@pytest.mark.asyncio
async def test_download_resource_http(agent):
    url = "https://example.com/image.png"
    
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"image data")
        
        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value=mock_get)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        result = await agent._download_resource(url, "images", 0)
        
        assert Path(result).exists()
        assert Path(result).read_bytes() == b"image data"


@pytest.mark.asyncio
async def test_download_resource_http_error(agent):
    url = "https://example.com/image.png"
    
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = MagicMock()
        mock_response.status = 404
        
        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value=mock_get)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        with pytest.raises(DownloadError, match="HTTP 404"):
            await agent._download_resource(url, "images", 0)


def test_validate_inputs_invalid_images(agent, sample_storyboard):
    with pytest.raises(ValidationError, match="Images must be a list"):
        agent._validate_inputs("not a list", [], sample_storyboard)


def test_validate_inputs_invalid_audios(agent, sample_storyboard):
    with pytest.raises(ValidationError, match="Audios must be a list"):
        agent._validate_inputs([], "not a list", sample_storyboard)


def test_validate_inputs_invalid_storyboard(agent):
    with pytest.raises(ValidationError, match="Storyboard must be a dictionary"):
        agent._validate_inputs([], [], "not a dict")


def test_validate_inputs_missing_scenes(agent):
    with pytest.raises(ValidationError, match="must have 'scenes' key"):
        agent._validate_inputs([], [], {})


def test_validate_inputs_empty_images(agent, sample_storyboard):
    with pytest.raises(ValidationError, match="Images list cannot be empty"):
        agent._validate_inputs([], ["audio1"], sample_storyboard)


def test_validate_inputs_empty_audios(agent, sample_storyboard):
    with pytest.raises(ValidationError, match="Audios list cannot be empty"):
        agent._validate_inputs(["image1"], [], sample_storyboard)


@pytest.mark.asyncio
async def test_create_scene_clip_success(agent, temp_dir):
    image_path = Path(temp_dir) / "image.png"
    audio_path = Path(temp_dir) / "audio.mp3"
    image_path.write_bytes(b"image")
    audio_path.write_bytes(b"audio")
    
    scene = {"scene_id": 1, "duration": 3.0}
    
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_process
        
        result = await agent._create_scene_clip(str(image_path), str(audio_path), scene, 0)
        
        assert "clip_0.mp4" in result
        assert mock_subprocess.called


@pytest.mark.asyncio
async def test_create_scene_clip_ffmpeg_error(agent, temp_dir):
    image_path = Path(temp_dir) / "image.png"
    audio_path = Path(temp_dir) / "audio.mp3"
    image_path.write_bytes(b"image")
    audio_path.write_bytes(b"audio")
    
    scene = {"scene_id": 1, "duration": 3.0}
    
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"FFmpeg error"))
        mock_subprocess.return_value = mock_process
        
        with pytest.raises(CompositionError, match="FFmpeg failed"):
            await agent._create_scene_clip(str(image_path), str(audio_path), scene, 0)


@pytest.mark.asyncio
async def test_concatenate_clips_success(agent, temp_dir):
    clip1 = Path(temp_dir) / "clip1.mp4"
    clip2 = Path(temp_dir) / "clip2.mp4"
    clip1.write_bytes(b"clip1")
    clip2.write_bytes(b"clip2")
    
    clips = [str(clip1), str(clip2)]
    
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_process
        
        result = await agent._concatenate_clips(clips)
        
        assert "final_" in result
        assert ".mp4" in result
        assert mock_subprocess.called


@pytest.mark.asyncio
async def test_concatenate_clips_error(agent, temp_dir):
    clips = [str(Path(temp_dir) / "clip1.mp4")]
    
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Concat error"))
        mock_subprocess.return_value = mock_process
        
        with pytest.raises(CompositionError, match="concatenation failed"):
            await agent._concatenate_clips(clips)


@pytest.mark.asyncio
async def test_get_video_duration_success(agent, temp_dir):
    video_path = Path(temp_dir) / "video.mp4"
    video_path.write_bytes(b"video")
    
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(
            return_value=(b'{"format": {"duration": "10.5"}}', b"")
        )
        mock_subprocess.return_value = mock_process
        
        duration = await agent._get_video_duration(str(video_path))
        
        assert duration == 10.5


@pytest.mark.asyncio
async def test_get_video_duration_error(agent, temp_dir):
    video_path = Path(temp_dir) / "video.mp4"
    video_path.write_bytes(b"video")
    
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error"))
        mock_subprocess.return_value = mock_process
        
        duration = await agent._get_video_duration(str(video_path))
        
        assert duration == 0.0


def test_cleanup_temp_files(agent, temp_dir):
    file1 = Path(temp_dir) / "temp1.txt"
    file2 = Path(temp_dir) / "temp2.txt"
    file1.write_text("temp")
    file2.write_text("temp")
    
    agent._cleanup_temp_files([str(file1), str(file2)])
    
    assert not file1.exists()
    assert not file2.exists()
