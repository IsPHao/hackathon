from typing import Dict, Any, Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class PipelineContext:
    """
    Pipeline执行上下文
    
    存储Pipeline执行过程中Agent间共享的数据,
    提供统一的数据访问接口,避免硬编码数据传递。
    
    Attributes:
        project_id: 项目唯一标识符
        data: 存储共享数据的字典
    """
    
    def __init__(self, project_id: UUID):
        """
        初始化Pipeline上下文
        
        Args:
            project_id: 项目唯一标识符
        """
        self.project_id = project_id
        self.data: Dict[str, Any] = {}
        logger.debug(f"PipelineContext initialized for project {project_id}")
    
    def set(self, key: str, value: Any) -> None:
        """
        设置共享数据
        
        Args:
            key: 数据键
            value: 数据值
        """
        self.data[key] = value
        logger.debug(f"Context set: {key}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取共享数据
        
        Args:
            key: 数据键
            default: 默认值(当键不存在时返回)
        
        Returns:
            Any: 数据值或默认值
        """
        value = self.data.get(key, default)
        if value is None and default is None:
            logger.warning(f"Context key '{key}' not found")
        return value
    
    def has(self, key: str) -> bool:
        """
        检查数据是否存在
        
        Args:
            key: 数据键
        
        Returns:
            bool: True表示存在,False表示不存在
        """
        return key in self.data
    
    def remove(self, key: str) -> None:
        """
        移除数据
        
        Args:
            key: 数据键
        """
        if key in self.data:
            del self.data[key]
            logger.debug(f"Context removed: {key}")
    
    def clear(self) -> None:
        """清空所有数据"""
        self.data.clear()
        logger.debug("Context cleared")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            Dict[str, Any]: 包含所有数据的字典
        """
        return {
            "project_id": str(self.project_id),
            "data": self.data.copy()
        }
