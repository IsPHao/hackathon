import pytest

from src.agents.voice_synthesizer import (
    VoiceSynthesizerError,
    ValidationError,
    SynthesisError,
    APIError,
)


def test_voice_synthesizer_error():
    error = VoiceSynthesizerError("test error")
    assert str(error) == "test error"
    assert isinstance(error, Exception)


def test_validation_error():
    error = ValidationError("validation failed")
    assert str(error) == "validation failed"
    assert isinstance(error, VoiceSynthesizerError)


def test_synthesis_error():
    error = SynthesisError("synthesis failed")
    assert str(error) == "synthesis failed"
    assert isinstance(error, VoiceSynthesizerError)


def test_api_error():
    error = APIError("API call failed")
    assert str(error) == "API call failed"
    assert isinstance(error, VoiceSynthesizerError)
