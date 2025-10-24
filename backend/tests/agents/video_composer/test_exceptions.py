import pytest

from src.agents.video_composer.exceptions import (
    VideoComposerError,
    ValidationError,
    CompositionError,
    StorageError,
    DownloadError,
)


def test_video_composer_error():
    error = VideoComposerError("test error")
    assert str(error) == "test error"
    assert isinstance(error, Exception)


def test_validation_error():
    error = ValidationError("validation failed")
    assert str(error) == "validation failed"
    assert isinstance(error, VideoComposerError)


def test_composition_error():
    error = CompositionError("composition failed")
    assert str(error) == "composition failed"
    assert isinstance(error, VideoComposerError)


def test_storage_error():
    error = StorageError("storage failed")
    assert str(error) == "storage failed"
    assert isinstance(error, VideoComposerError)


def test_download_error():
    error = DownloadError("download failed")
    assert str(error) == "download failed"
    assert isinstance(error, VideoComposerError)
