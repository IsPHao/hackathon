import pytest
from src.agents.character_consistency import (
    CharacterConsistencyError,
    ValidationError,
    StorageError,
    GenerationError,
)


def test_character_consistency_error():
    error = CharacterConsistencyError("test error")
    assert str(error) == "test error"
    assert isinstance(error, Exception)


def test_validation_error():
    error = ValidationError("validation failed")
    assert str(error) == "validation failed"
    assert isinstance(error, CharacterConsistencyError)


def test_storage_error():
    error = StorageError("storage failed")
    assert str(error) == "storage failed"
    assert isinstance(error, CharacterConsistencyError)


def test_generation_error():
    error = GenerationError("generation failed")
    assert str(error) == "generation failed"
    assert isinstance(error, CharacterConsistencyError)
