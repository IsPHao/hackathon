import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from backend.src.core.error_handler import ErrorHandler
from backend.src.core.exceptions import APIError, ValidationError


@pytest.fixture
def error_handler():
    return ErrorHandler()


@pytest.mark.asyncio
async def test_handle_api_error(error_handler):
    project_id = uuid4()
    error = APIError("API call failed")
    context = {"endpoint": "/api/generate"}
    
    with patch.object(error_handler, '_report_error', new=AsyncMock()) as mock_report:
        with patch.object(error_handler, '_attempt_recovery', new=AsyncMock()) as mock_recovery:
            await error_handler.handle(project_id, error, context)
            
            mock_report.assert_called_once()
            mock_recovery.assert_called_once()


@pytest.mark.asyncio
async def test_handle_validation_error(error_handler):
    project_id = uuid4()
    error = ValidationError("Invalid input")
    
    with patch.object(error_handler, '_report_error', new=AsyncMock()) as mock_report:
        with patch.object(error_handler, '_attempt_recovery', new=AsyncMock()) as mock_recovery:
            await error_handler.handle(project_id, error)
            
            mock_report.assert_called_once()
            mock_recovery.assert_not_called()


@pytest.mark.asyncio
async def test_classify_api_error(error_handler):
    error = APIError("Test")
    error_type = error_handler._classify_error(error)
    assert error_type == "api_error"


@pytest.mark.asyncio
async def test_classify_validation_error(error_handler):
    error = ValidationError("Test")
    error_type = error_handler._classify_error(error)
    assert error_type == "validation_error"


@pytest.mark.asyncio
async def test_classify_timeout_error(error_handler):
    error = TimeoutError("Test")
    error_type = error_handler._classify_error(error)
    assert error_type == "timeout_error"


@pytest.mark.asyncio
async def test_classify_unknown_error(error_handler):
    error = Exception("Test")
    error_type = error_handler._classify_error(error)
    assert error_type == "unknown_error"


@pytest.mark.asyncio
async def test_is_recoverable(error_handler):
    assert error_handler._is_recoverable("api_error") is True
    assert error_handler._is_recoverable("timeout_error") is True
    assert error_handler._is_recoverable("validation_error") is False
    assert error_handler._is_recoverable("unknown_error") is False
