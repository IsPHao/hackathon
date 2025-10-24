from abc import ABC, abstractmethod
from typing import Any, Dict
from uuid import UUID


class Agent(ABC):
    """
    Agent基类
    
    所有Agent必须继承此类并实现execute方法。
    """
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        执行Agent的核心逻辑
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            Any: Agent执行结果
        """
        pass


class Pipeline(ABC):
    """
    Pipeline基类
    
    所有Pipeline必须继承此类并实现execute方法。
    """
    
    @abstractmethod
    async def execute(self, project_id: UUID, *args, **kwargs) -> Dict[str, Any]:
        """
        执行Pipeline的工作流
        
        Args:
            project_id: 项目唯一标识符
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            Dict[str, Any]: Pipeline执行结果
        """
        pass
