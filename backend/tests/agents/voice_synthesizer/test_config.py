import pytest
from pydantic import ValidationError as PydanticValidationError

from src.agents.voice_synthesizer import VoiceSynthesizerConfig


def test_default_config():
    config = VoiceSynthesizerConfig()
    assert config.qiniu_api_key == ""
    assert config.qiniu_endpoint == "https://openai.qiniu.com"
    assert config.voice_type == "qiniu_zh_female_wwxkjx"
    assert config.encoding == "mp3"
    assert config.speed_ratio == 1.0
    assert config.audio_format == "mp3"
    assert config.enable_post_processing is False
    assert config.fade_duration == 100
    assert config.max_text_length == 4096


def test_custom_config():
    config = VoiceSynthesizerConfig(
        qiniu_api_key="test_key",
        voice_type="qiniu_zh_male_test",
        encoding="wav",
        speed_ratio=1.5,
        audio_format="wav",
        enable_post_processing=True,
        fade_duration=200,
        max_text_length=2048
    )
    assert config.qiniu_api_key == "test_key"
    assert config.voice_type == "qiniu_zh_male_test"
    assert config.encoding == "wav"
    assert config.speed_ratio == 1.5
    assert config.audio_format == "wav"
    assert config.enable_post_processing is True
    assert config.fade_duration == 200
    assert config.max_text_length == 2048


def test_speed_ratio_validation():
    with pytest.raises(PydanticValidationError):
        VoiceSynthesizerConfig(speed_ratio=0.1)
    
    with pytest.raises(PydanticValidationError):
        VoiceSynthesizerConfig(speed_ratio=5.0)


def test_fade_duration_validation():
    with pytest.raises(PydanticValidationError):
        VoiceSynthesizerConfig(fade_duration=-10)
    
    config = VoiceSynthesizerConfig(fade_duration=0)
    assert config.fade_duration == 0