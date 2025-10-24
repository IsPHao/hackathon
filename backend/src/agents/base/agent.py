from typing import TypeVar, Generic, Optional, Any
from abc import ABC, abstractmethod
import logging
from pydantic import BaseModel

from .exceptions import ValidationError

ConfigT = TypeVar('ConfigT', bound=BaseModel)


class BaseAgent(ABC, Generic[ConfigT]):
    """
    基础Agent类
    
    所有Agent必须继承此类并实现execute方法。
    提供统一的接口和公共功能。
    """
    
    def __init__(self, config: Optional[ConfigT] = None):
        self.config = config or self._default_config()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def _default_config(self) -> ConfigT:
        """返回默认配置"""
        pass
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        执行Agent的核心逻辑(统一接口)
        
        所有Agent必须实现此方法。可以在此方法中调用专用方法(如parse、generate等)。
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            Any: Agent执行结果
        """
        pass
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        检查Agent是否就绪,配置是否正确。
        子类可以重写此方法以实现自定义检查。
        
        Returns:
            bool: True表示健康,False表示存在问题
        """
        try:
            self.logger.info(f"{self.__class__.__name__} health check: OK")
            return True
        except Exception as e:
            self.logger.error(f"{self.__class__.__name__} health check failed: {e}")
            return False
    
    def _validate_not_empty(self, value, field_name: str):
        if not value:
            raise ValidationError(f"{field_name} cannot be empty")
    
    def _validate_type(self, value, expected_type, field_name: str):
        if not isinstance(value, expected_type):
            raise ValidationError(
                f"{field_name} must be {expected_type.__name__}, got {type(value).__name__}"
            )
    
    def _validate_list_not_empty(self, value, field_name: str):
        if not isinstance(value, list):
            raise ValidationError(f"{field_name} must be a list")
        if not value:
            raise ValidationError(f"{field_name} cannot be empty")
