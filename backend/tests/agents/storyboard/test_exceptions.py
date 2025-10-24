import pytest
from src.agents.storyboard import (
    StoryboardError,
    ValidationError,
    ProcessError,
    APIError,
)


def test_storyboard_error():
    error = StoryboardError("test error")
    assert str(error) == "test error"
    assert isinstance(error, Exception)


def test_validation_error():
    error = ValidationError("validation failed")
    assert str(error) == "validation failed"
    assert isinstance(error, StoryboardError)


def test_process_error():
    error = ProcessError("process failed")
    assert str(error) == "process failed"
    assert isinstance(error, StoryboardError)


def test_api_error():
    error = APIError("api call failed")
    assert str(error) == "api call failed"
    assert isinstance(error, StoryboardError)
