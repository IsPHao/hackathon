from typing import TypeVar, Generic, Optional
from abc import ABC, abstractmethod
import logging
from pydantic import BaseModel

from .exceptions import ValidationError

ConfigT = TypeVar('ConfigT', bound=BaseModel)


class BaseAgent(ABC, Generic[ConfigT]):
    
    def __init__(self, config: Optional[ConfigT] = None):
        self.config = config or self._default_config()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def _default_config(self) -> ConfigT:
        pass
    
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
