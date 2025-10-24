import pytest
from pydantic import ValidationError as PydanticValidationError

from src.agents.voice_synthesizer import VoiceSynthesizerConfig


def test_default_config():
    config = VoiceSynthesizerConfig()
    assert config.model == "tts-1"
    assert config.speed == 1.0
    assert config.audio_format == "mp3"
    assert config.enable_post_processing is True
    assert config.fade_duration == 100
    assert config.max_text_length == 4096
    assert "male_young" in config.voice_mapping
    assert "narrator" in config.voice_mapping


def test_custom_config():
    config = VoiceSynthesizerConfig(
        model="tts-1-hd",
        speed=1.5,
        audio_format="wav",
        enable_post_processing=False,
        fade_duration=200,
        max_text_length=2048
    )
    assert config.model == "tts-1-hd"
    assert config.speed == 1.5
    assert config.audio_format == "wav"
    assert config.enable_post_processing is False
    assert config.fade_duration == 200
    assert config.max_text_length == 2048


def test_custom_voice_mapping():
    custom_mapping = {
        "hero": "alloy",
        "villain": "onyx"
    }
    config = VoiceSynthesizerConfig(voice_mapping=custom_mapping)
    assert config.voice_mapping == custom_mapping


def test_speed_validation():
    with pytest.raises(PydanticValidationError):
        VoiceSynthesizerConfig(speed=0.1)
    
    with pytest.raises(PydanticValidationError):
        VoiceSynthesizerConfig(speed=5.0)


def test_fade_duration_validation():
    with pytest.raises(PydanticValidationError):
        VoiceSynthesizerConfig(fade_duration=-10)
    
    config = VoiceSynthesizerConfig(fade_duration=0)
    assert config.fade_duration == 0
