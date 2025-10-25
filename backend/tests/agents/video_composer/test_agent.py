import pytest
from pathlib import Path
import tempfile
import shutil
import os

from src.agents.video_composer import (
    VideoComposerAgent,
    VideoSegment,
    AudioSegment,
    VideoComposerConfig,
    ValidationError,
    CompositionError,
)


@pytest.fixture
def temp_dir():
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def agent(fake_storage):
    config = VideoComposerConfig(timeout=60)
    return VideoComposerAgent(
        task_id="test-task-123",
        config=config,
        storage=fake_storage
    )


@pytest.fixture
def sample_video_files(temp_dir):
    video_files = []
    for i in range(3):
        video_path = Path(temp_dir) / f"video_{i}.mp4"
        video_path.write_bytes(b"fake video data")
        video_files.append(str(video_path))
    return video_files


@pytest.fixture
def sample_audio_files(temp_dir):
    audio_files = []
    for i in range(3):
        audio_path = Path(temp_dir) / f"audio_{i}.mp3"
        audio_path.write_bytes(b"fake audio data")
        audio_files.append(str(audio_path))
    return audio_files


def test_video_segment_creation():
    segment = VideoSegment(path="/path/to/video.mp4", duration=5.0)
    assert segment.path == "/path/to/video.mp4"
    assert segment.duration == 5.0
    assert segment.width is None
    assert segment.height is None


def test_video_segment_with_metadata():
    segment = VideoSegment(
        path="/path/to/video.mp4",
        duration=5.0,
        width=1920,
        height=1080,
        format="mp4"
    )
    assert segment.width == 1920
    assert segment.height == 1080
    assert segment.format == "mp4"


def test_video_segment_invalid_duration():
    with pytest.raises(ValueError):
        VideoSegment(path="/path/to/video.mp4", duration=0)
    
    with pytest.raises(ValueError):
        VideoSegment(path="/path/to/video.mp4", duration=-1)


def test_audio_segment_creation():
    segment = AudioSegment(path="/path/to/audio.mp3", duration=5.0)
    assert segment.path == "/path/to/audio.mp3"
    assert segment.duration == 5.0
    assert segment.format is None
    assert segment.bitrate is None


def test_audio_segment_with_metadata():
    segment = AudioSegment(
        path="/path/to/audio.mp3",
        duration=5.0,
        format="mp3",
        bitrate="128k"
    )
    assert segment.format == "mp3"
    assert segment.bitrate == "128k"


def test_audio_segment_invalid_duration():
    with pytest.raises(ValueError):
        AudioSegment(path="/path/to/audio.mp3", duration=0)
    
    with pytest.raises(ValueError):
        AudioSegment(path="/path/to/audio.mp3", duration=-1)


def test_validate_segments_valid(agent, sample_video_files, sample_audio_files):
    video_segments = [
        VideoSegment(path=sample_video_files[0], duration=3.0),
        VideoSegment(path=sample_video_files[1], duration=5.0),
    ]
    audio_segments = [
        AudioSegment(path=sample_audio_files[0], duration=3.0),
        AudioSegment(path=sample_audio_files[1], duration=5.0),
    ]
    
    agent._validate_segments(video_segments, audio_segments)


def test_validate_segments_not_list(agent):
    with pytest.raises(ValidationError, match="video_segments 必须是列表"):
        agent._validate_segments("not a list", [])
    
    with pytest.raises(ValidationError, match="audio_segments 必须是列表"):
        agent._validate_segments([], "not a list")


def test_validate_segments_empty_list(agent):
    with pytest.raises(ValidationError, match="video_segments 不能为空"):
        agent._validate_segments([], [AudioSegment(path="/path/audio.mp3", duration=1.0)])
    
    with pytest.raises(ValidationError, match="audio_segments 不能为空"):
        agent._validate_segments([VideoSegment(path="/path/video.mp4", duration=1.0)], [])


def test_validate_segments_wrong_type(agent):
    with pytest.raises(ValidationError, match="video_segments\\[0\\] 必须是 VideoSegment 类型"):
        agent._validate_segments(["not a segment"], [AudioSegment(path="/path/audio.mp3", duration=1.0)])
    
    with pytest.raises(ValidationError, match="audio_segments\\[0\\] 必须是 AudioSegment 类型"):
        agent._validate_segments([VideoSegment(path="/path/video.mp4", duration=1.0)], ["not a segment"])


def test_validate_segments_invalid_duration(agent):
    video_seg = VideoSegment(path="/path/video.mp4", duration=1.0)
    audio_seg = AudioSegment(path="/path/audio.mp3", duration=1.0)
    
    video_seg_invalid = VideoSegment.__new__(VideoSegment)
    video_seg_invalid.path = "/path/video.mp4"
    video_seg_invalid.duration = 0
    
    with pytest.raises(ValidationError, match="video_segments\\[0\\] 的时长必须大于0"):
        agent._validate_segments([video_seg_invalid], [audio_seg])
    
    audio_seg_invalid = AudioSegment.__new__(AudioSegment)
    audio_seg_invalid.path = "/path/audio.mp3"
    audio_seg_invalid.duration = -1
    
    with pytest.raises(ValidationError, match="audio_segments\\[0\\] 的时长必须大于0"):
        agent._validate_segments([video_seg], [audio_seg_invalid])


def test_check_files_exist_valid(agent, sample_video_files, sample_audio_files):
    video_segments = [VideoSegment(path=sample_video_files[0], duration=3.0)]
    audio_segments = [AudioSegment(path=sample_audio_files[0], duration=3.0)]
    
    agent._check_files_exist(video_segments, audio_segments)


def test_check_files_exist_missing_video(agent, sample_audio_files):
    video_segments = [VideoSegment(path="/nonexistent/video.mp4", duration=3.0)]
    audio_segments = [AudioSegment(path=sample_audio_files[0], duration=3.0)]
    
    with pytest.raises(ValidationError, match="视频文件不存在"):
        agent._check_files_exist(video_segments, audio_segments)


def test_check_files_exist_missing_audio(agent, sample_video_files):
    video_segments = [VideoSegment(path=sample_video_files[0], duration=3.0)]
    audio_segments = [AudioSegment(path="/nonexistent/audio.mp3", duration=3.0)]
    
    with pytest.raises(ValidationError, match="音频文件不存在"):
        agent._check_files_exist(video_segments, audio_segments)


def test_check_files_exist_video_is_directory(agent, sample_audio_files, temp_dir):
    video_dir = Path(temp_dir) / "video_dir"
    video_dir.mkdir()
    
    video_segments = [VideoSegment(path=str(video_dir), duration=3.0)]
    audio_segments = [AudioSegment(path=sample_audio_files[0], duration=3.0)]
    
    with pytest.raises(ValidationError, match="视频路径不是文件"):
        agent._check_files_exist(video_segments, audio_segments)


def test_check_files_exist_audio_is_directory(agent, sample_video_files, temp_dir):
    audio_dir = Path(temp_dir) / "audio_dir"
    audio_dir.mkdir()
    
    video_segments = [VideoSegment(path=sample_video_files[0], duration=3.0)]
    audio_segments = [AudioSegment(path=str(audio_dir), duration=3.0)]
    
    with pytest.raises(ValidationError, match="音频路径不是文件"):
        agent._check_files_exist(video_segments, audio_segments)


@pytest.mark.asyncio
async def test_compose_video_mismatched_count(agent, sample_video_files, sample_audio_files):
    video_segments = [
        VideoSegment(path=sample_video_files[0], duration=3.0),
        VideoSegment(path=sample_video_files[1], duration=5.0),
    ]
    audio_segments = [
        AudioSegment(path=sample_audio_files[0], duration=3.0),
    ]
    
    with pytest.raises(ValidationError, match="视频片段数量.*必须与音频片段数量.*相同"):
        await agent.compose_video(video_segments, audio_segments)


@pytest.mark.asyncio
async def test_compose_video_single_segment(agent, sample_video_files, sample_audio_files, monkeypatch):
    video_segments = [VideoSegment(path=sample_video_files[0], duration=3.0)]
    audio_segments = [AudioSegment(path=sample_audio_files[0], duration=3.0)]
    
    async def mock_merge(video_path, audio_path, index):
        return f"/tmp/clip_{index}.mp4"
    
    async def mock_concatenate(clips, output_path):
        Path(output_path).write_bytes(b"final video")
        return output_path
    
    async def mock_get_duration(video_path):
        return 3.0
    
    monkeypatch.setattr(agent, "_merge_video_audio", mock_merge)
    monkeypatch.setattr(agent, "_concatenate_clips", mock_concatenate)
    monkeypatch.setattr(agent, "_get_video_duration", mock_get_duration)
    
    result = await agent.compose_video(video_segments, audio_segments)
    
    assert "output_path" in result
    assert "duration" in result
    assert "file_size" in result
    assert result["duration"] == 3.0
    assert result["file_size"] > 0


@pytest.mark.asyncio
async def test_compose_video_multiple_segments(agent, sample_video_files, sample_audio_files, monkeypatch):
    video_segments = [
        VideoSegment(path=sample_video_files[0], duration=3.0),
        VideoSegment(path=sample_video_files[1], duration=5.0),
        VideoSegment(path=sample_video_files[2], duration=4.0),
    ]
    audio_segments = [
        AudioSegment(path=sample_audio_files[0], duration=3.0),
        AudioSegment(path=sample_audio_files[1], duration=5.0),
        AudioSegment(path=sample_audio_files[2], duration=4.0),
    ]
    
    merge_calls = []
    
    async def mock_merge(video_path, audio_path, index):
        merge_calls.append({"video": video_path, "audio": audio_path, "index": index})
        return f"/tmp/clip_{index}.mp4"
    
    async def mock_concatenate(clips, output_path):
        Path(output_path).write_bytes(b"final video")
        return output_path
    
    async def mock_get_duration(video_path):
        return 12.0
    
    monkeypatch.setattr(agent, "_merge_video_audio", mock_merge)
    monkeypatch.setattr(agent, "_concatenate_clips", mock_concatenate)
    monkeypatch.setattr(agent, "_get_video_duration", mock_get_duration)
    
    result = await agent.compose_video(video_segments, audio_segments)
    
    assert len(merge_calls) == 3
    assert merge_calls[0]["index"] == 0
    assert merge_calls[1]["index"] == 1
    assert merge_calls[2]["index"] == 2
    assert result["duration"] == 12.0


@pytest.mark.asyncio
async def test_compose_video_with_custom_output_path(agent, sample_video_files, sample_audio_files, temp_dir, monkeypatch):
    video_segments = [VideoSegment(path=sample_video_files[0], duration=3.0)]
    audio_segments = [AudioSegment(path=sample_audio_files[0], duration=3.0)]
    
    custom_output = str(Path(temp_dir) / "custom_output.mp4")
    
    async def mock_merge(video_path, audio_path, index):
        return f"/tmp/clip_{index}.mp4"
    
    async def mock_concatenate(clips, output_path):
        Path(output_path).write_bytes(b"final video")
        return output_path
    
    async def mock_get_duration(video_path):
        return 3.0
    
    monkeypatch.setattr(agent, "_merge_video_audio", mock_merge)
    monkeypatch.setattr(agent, "_concatenate_clips", mock_concatenate)
    monkeypatch.setattr(agent, "_get_video_duration", mock_get_duration)
    
    result = await agent.compose_video(video_segments, audio_segments, output_path=custom_output)
    
    assert result["output_path"] == custom_output


@pytest.mark.asyncio
async def test_health_check_success(agent):
    result = await agent.health_check()
    assert isinstance(result, bool)


def test_cleanup_temp_files(agent):
    temp_dir = agent.temp_dir
    test_file = temp_dir / "test.txt"
    test_file.write_text("test")
    
    assert temp_dir.exists()
    assert test_file.exists()
    
    agent.cleanup_temp_files()
    
    assert not temp_dir.exists()


def test_agent_initialization(fake_storage):
    config = VideoComposerConfig(timeout=120)
    agent = VideoComposerAgent(
        task_id="custom-task",
        config=config,
        storage=fake_storage
    )
    
    assert agent.task_id == "custom-task"
    assert agent.config.timeout == 120
    assert agent.storage == fake_storage


def test_config_defaults():
    config = VideoComposerConfig()
    
    assert config.timeout > 0
    assert hasattr(config, 'storage_type')
    assert hasattr(config, 'audio_codec')
    assert hasattr(config, 'audio_bitrate')


def test_temp_directory_creation(agent):
    assert agent.temp_dir is not None
    assert isinstance(agent.temp_dir, Path)
    assert agent.temp_dir.exists()
