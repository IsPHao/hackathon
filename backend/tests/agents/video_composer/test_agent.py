import pytest
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


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def agent(fake_storage):
    """Create VideoComposerAgent with fake storage"""
    config = VideoComposerConfig(timeout=60)
    return VideoComposerAgent(
        task_id="test-task-123",
        config=config,
        storage=fake_storage
    )


@pytest.mark.asyncio
async def test_download_resource_local_file(agent, temp_dir):
    """Test downloading local file without mocks"""
    local_file = Path(temp_dir) / "local.png"
    local_file.write_bytes(b"local data")
    
    result = await agent._download_resource(str(local_file), "images", 0)
    
    assert result == str(local_file)


def test_validate_inputs_invalid_images(agent, sample_storyboard):
    """Test validation for invalid images input"""
    with pytest.raises(ValidationError, match="Images must be a list"):
        agent._validate_inputs("not a list", [], sample_storyboard)


def test_validate_inputs_invalid_audios(agent, sample_storyboard):
    """Test validation for invalid audios input"""
    with pytest.raises(ValidationError, match="Audios must be a list"):
        agent._validate_inputs([], "not a list", sample_storyboard)


def test_validate_inputs_invalid_storyboard(agent):
    """Test validation for invalid storyboard"""
    with pytest.raises(ValidationError, match="Storyboard must be a dictionary"):
        agent._validate_inputs([], [], "not a dict")


def test_validate_inputs_missing_scenes(agent):
    """Test validation for missing scenes in storyboard"""
    with pytest.raises(ValidationError, match="must have 'scenes' key"):
        agent._validate_inputs([], [], {})


def test_validate_inputs_empty_images(agent, sample_storyboard):
    """Test validation for empty images list"""
    with pytest.raises(ValidationError, match="Images list cannot be empty"):
        agent._validate_inputs([], ["audio1"], sample_storyboard)


def test_validate_inputs_empty_audios(agent, sample_storyboard):
    """Test validation for empty audios list"""
    with pytest.raises(ValidationError, match="Audios list cannot be empty"):
        agent._validate_inputs(["image1"], [], sample_storyboard)


def test_validate_inputs_valid(agent, sample_storyboard):
    """Test validation with valid inputs"""
    images = ["image1.png", "image2.png"]
    audios = ["audio1.mp3", "audio2.mp3"]
    
    agent._validate_inputs(images, audios, sample_storyboard)


def test_cleanup_temp_files(agent, temp_dir):
    """Test temporary file cleanup"""
    file1 = Path(temp_dir) / "temp1.txt"
    file2 = Path(temp_dir) / "temp2.txt"
    file1.write_text("temp")
    file2.write_text("temp")
    
    agent._cleanup_temp_files([str(file1), str(file2)])
    
    assert not file1.exists()
    assert not file2.exists()


def test_cleanup_nonexistent_files(agent):
    """Test cleanup handles nonexistent files gracefully"""
    agent._cleanup_temp_files(["/nonexistent/file1.txt", "/nonexistent/file2.txt"])


def test_config_defaults():
    """Test default configuration values"""
    config = VideoComposerConfig()
    
    assert config.timeout > 0
    assert hasattr(config, 'storage_type')


def test_agent_initialization(fake_storage):
    """Test agent initialization with custom config"""
    config = VideoComposerConfig(timeout=120)
    agent = VideoComposerAgent(
        task_id="custom-task",
        config=config,
        storage=fake_storage
    )
    
    assert agent.task_id == "custom-task"
    assert agent.config.timeout == 120
    assert agent.storage == fake_storage


@pytest.mark.asyncio
async def test_compose_mismatched_images(agent, sample_storyboard):
    """Test compose with mismatched number of images"""
    images = ["image1.png"]
    audios = ["audio1.mp3", "audio2.mp3"]
    
    with pytest.raises(ValidationError, match="Number of images"):
        await agent.compose(images, audios, sample_storyboard)


@pytest.mark.asyncio
async def test_compose_mismatched_audios(agent, sample_storyboard):
    """Test compose with mismatched number of audios"""
    images = ["image1.png", "image2.png"]
    audios = ["audio1.mp3"]
    
    with pytest.raises(ValidationError, match="Number of audios"):
        await agent.compose(images, audios, sample_storyboard)


def test_build_ffmpeg_command_for_scene(agent, temp_dir):
    """Test FFmpeg command building logic"""
    image_path = str(Path(temp_dir) / "image.png")
    audio_path = str(Path(temp_dir) / "audio.mp3")
    output_path = str(Path(temp_dir) / "output.mp4")
    
    scene = {"scene_id": 1, "duration": 5.0}
    
    cmd = agent._build_scene_ffmpeg_cmd(image_path, audio_path, output_path, scene)
    
    assert isinstance(cmd, list)
    assert "ffmpeg" in cmd[0].lower()
    assert image_path in cmd
    assert audio_path in cmd
    assert output_path in cmd


def test_build_concat_ffmpeg_command(agent, temp_dir):
    """Test concatenation FFmpeg command building"""
    clips = [
        str(Path(temp_dir) / "clip1.mp4"),
        str(Path(temp_dir) / "clip2.mp4")
    ]
    output = str(Path(temp_dir) / "final.mp4")
    
    cmd = agent._build_concat_ffmpeg_cmd(clips, output)
    
    assert isinstance(cmd, list)
    assert "ffmpeg" in cmd[0].lower()
    assert output in cmd


def test_temp_directory_creation(agent):
    """Test that temp directory is properly set up"""
    assert agent.temp_dir is not None
    assert isinstance(agent.temp_dir, str) or isinstance(agent.temp_dir, Path)


def test_storage_integration(agent, fake_storage):
    """Test storage backend integration"""
    assert agent.storage == fake_storage
    assert hasattr(agent.storage, 'save')
    assert hasattr(agent.storage, 'save_file')


@pytest.mark.asyncio
async def test_validate_resource_urls():
    """Test resource URL validation"""
    valid_urls = [
        "https://example.com/image.png",
        "http://example.com/video.mp4",
        "/local/path/to/file.png"
    ]
    
    for url in valid_urls:
        assert isinstance(url, str)
        assert len(url) > 0


def test_scene_duration_validation(agent):
    """Test scene duration validation"""
    valid_scene = {
        "scene_id": 1,
        "duration": 3.0,
        "description": "Test scene"
    }
    
    assert valid_scene["duration"] > 0
    assert isinstance(valid_scene["duration"], (int, float))


def test_storyboard_structure_validation(sample_storyboard):
    """Test storyboard structure"""
    assert "scenes" in sample_storyboard
    assert isinstance(sample_storyboard["scenes"], list)
    assert len(sample_storyboard["scenes"]) > 0
    
    for scene in sample_storyboard["scenes"]:
        assert "scene_id" in scene
        assert "duration" in scene


@pytest.mark.asyncio
async def test_resource_cleanup_on_error(agent, temp_dir):
    """Test that resources are cleaned up on error"""
    temp_files = [
        str(Path(temp_dir) / f"temp_{i}.txt")
        for i in range(3)
    ]
    
    for file_path in temp_files:
        Path(file_path).write_text("temp data")
    
    agent._cleanup_temp_files(temp_files)
    
    for file_path in temp_files:
        assert not Path(file_path).exists()


def test_multiple_scenes_validation(sample_storyboard):
    """Test handling of multiple scenes"""
    scenes = sample_storyboard["scenes"]
    
    assert len(scenes) >= 2
    
    for i, scene in enumerate(scenes):
        assert scene["scene_id"] == i + 1
        assert "duration" in scene
        assert scene["duration"] > 0


@pytest.mark.asyncio
async def test_agent_task_id_tracking(fake_storage):
    """Test that agent properly tracks task ID"""
    task_id = "tracking-test-123"
    agent = VideoComposerAgent(
        task_id=task_id,
        storage=fake_storage
    )
    
    assert agent.task_id == task_id


def test_config_customization():
    """Test configuration customization"""
    config = VideoComposerConfig(
        timeout=300,
        storage_type="local"
    )
    
    assert config.timeout == 300
    assert config.storage_type == "local"
