import pytest
from src.agents.image_generator import (
    ImageGeneratorError,
    ValidationError,
    GenerationError,
    StorageError,
    APIError,
)


def test_exception_hierarchy():
    assert issubclass(ValidationError, ImageGeneratorError)
    assert issubclass(GenerationError, ImageGeneratorError)
    assert issubclass(StorageError, ImageGeneratorError)
    assert issubclass(APIError, ImageGeneratorError)


def test_validation_error():
    error = ValidationError("test message")
    assert str(error) == "test message"
    assert isinstance(error, ImageGeneratorError)


def test_generation_error():
    error = GenerationError("generation failed")
    assert str(error) == "generation failed"
    assert isinstance(error, ImageGeneratorError)


def test_storage_error():
    error = StorageError("storage failed")
    assert str(error) == "storage failed"
    assert isinstance(error, ImageGeneratorError)


def test_api_error():
    error = APIError("api error")
    assert str(error) == "api error"
    assert isinstance(error, ImageGeneratorError)
