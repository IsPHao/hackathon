import pytest

from src.agents.novel_parser import (
    NovelParserError,
    ValidationError,
    ParseError,
    APIError,
)


def test_novel_parser_error():
    error = NovelParserError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)


def test_validation_error():
    error = ValidationError("Validation failed")
    assert str(error) == "Validation failed"
    assert isinstance(error, NovelParserError)
    assert isinstance(error, Exception)


def test_parse_error():
    error = ParseError("Parse failed")
    assert str(error) == "Parse failed"
    assert isinstance(error, NovelParserError)
    assert isinstance(error, Exception)


def test_api_error():
    error = APIError("API call failed")
    assert str(error) == "API call failed"
    assert isinstance(error, NovelParserError)
    assert isinstance(error, Exception)


def test_exception_hierarchy():
    assert issubclass(ValidationError, NovelParserError)
    assert issubclass(ParseError, NovelParserError)
    assert issubclass(APIError, NovelParserError)
    assert issubclass(NovelParserError, Exception)
