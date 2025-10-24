import pytest
from pydantic import ValidationError

from src.agents.video_composer.config import VideoComposerConfig


def test_default_config():
    config = VideoComposerConfig()
    
    assert config.fps == 24
    assert config.resolution == "1920x1080"
    assert config.codec == "libx264"
    assert config.audio_codec == "aac"
    assert config.preset == "medium"
    assert config.bitrate == "5000k"
    assert config.audio_bitrate == "128k"
    assert config.temp_dir == "/tmp/video_composition"
    assert config.storage_type == "local"
    assert config.local_storage_path == "./data/videos"
    assert config.timeout == 300


def test_custom_config():
    config = VideoComposerConfig(
        fps=30,
        resolution="1280x720",
        preset="fast",
        storage_type="oss",
        oss_bucket="my-bucket",
    )
    
    assert config.fps == 30
    assert config.resolution == "1280x720"
    assert config.preset == "fast"
    assert config.storage_type == "oss"
    assert config.oss_bucket == "my-bucket"


def test_invalid_fps():
    with pytest.raises(ValidationError):
        VideoComposerConfig(fps=0)
    
    with pytest.raises(ValidationError):
        VideoComposerConfig(fps=100)


def test_invalid_preset():
    with pytest.raises(ValidationError):
        VideoComposerConfig(preset="invalid")


def test_invalid_storage_type():
    with pytest.raises(ValidationError):
        VideoComposerConfig(storage_type="invalid")


def test_invalid_timeout():
    with pytest.raises(ValidationError):
        VideoComposerConfig(timeout=10)
