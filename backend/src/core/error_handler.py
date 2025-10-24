from typing import Optional, Dict, Any
from uuid import UUID
import logging

from .exceptions import APIError, ValidationError

logger = logging.getLogger(__name__)


class ErrorHandler:
    
    async def handle(
        self,
        project_id: UUID,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ):
        logger.error(
            f"Error in project {project_id}: {error}",
            exc_info=True,
            extra=context or {}
        )
        
        error_type = self._classify_error(error)
        
        await self._report_error(project_id, error, error_type, context)
        
        if self._is_recoverable(error_type):
            await self._attempt_recovery(project_id, error, context)
    
    def _classify_error(self, error: Exception) -> str:
        if isinstance(error, APIError):
            return "api_error"
        elif isinstance(error, ValidationError):
            return "validation_error"
        elif isinstance(error, TimeoutError):
            return "timeout_error"
        else:
            return "unknown_error"
    
    async def _report_error(
        self,
        project_id: UUID,
        error: Exception,
        error_type: str,
        context: Optional[Dict[str, Any]]
    ):
        pass
    
    def _is_recoverable(self, error_type: str) -> bool:
        return error_type in ["api_error", "timeout_error"]
    
    async def _attempt_recovery(
        self,
        project_id: UUID,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ):
        pass
