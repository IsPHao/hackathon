from typing import Optional, Dict, Any
from uuid import UUID
import logging

from .exceptions import APIError, ValidationError

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    错误处理器
    
    负责捕获和记录错误，对错误进行分类，并尝试错误恢复。
    支持将错误上报到监控系统（如Sentry）。
    """
    
    async def handle(
        self,
        project_id: UUID,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        处理项目执行过程中的错误
        
        Args:
            project_id: 发生错误的项目ID
            error: 异常对象
            context: 额外的上下文信息（如当前阶段、参数等）
        """
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
        """
        对错误进行分类
        
        Args:
            error: 异常对象
        
        Returns:
            str: 错误类型（'api_error', 'validation_error', 'timeout_error', 'unknown_error'）
        """
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
        """
        将错误上报到监控系统
        
        TODO: 集成Sentry等错误追踪系统
        
        Args:
            project_id: 项目ID
            error: 异常对象
            error_type: 错误类型
            context: 上下文信息
        """
        logger.debug(
            f"Error reporting not implemented. "
            f"Project: {project_id}, Type: {error_type}, Error: {error}"
        )
    
    def _is_recoverable(self, error_type: str) -> bool:
        """
        判断错误是否可恢复
        
        Args:
            error_type: 错误类型
        
        Returns:
            bool: 是否可尝试恢复
        """
        return error_type in ["api_error", "timeout_error"]
    
    async def _attempt_recovery(
        self,
        project_id: UUID,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ):
        """
        尝试从错误中恢复
        
        实现基本的错误恢复策略：
        - API错误：记录错误，建议重试
        - 超时错误：记录错误，建议重试
        
        Args:
            project_id: 项目ID
            error: 异常对象
            context: 上下文信息
        """
        error_type = self._classify_error(error)
        
        if error_type == "api_error":
            logger.warning(
                f"API error occurred for project {project_id}. "
                f"Error: {error}. Caller should implement retry logic."
            )
        elif error_type == "timeout_error":
            logger.warning(
                f"Timeout error occurred for project {project_id}. "
                f"Error: {error}. Caller should implement retry with backoff."
            )
        else:
            logger.debug(
                f"Non-recoverable error for project {project_id}: {error}"
            )
