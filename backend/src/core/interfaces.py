from abc import ABC, abstractmethod
from typing import Any, Dict
from uuid import UUID


class Agent(ABC):
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        pass


class Pipeline(ABC):
    
    @abstractmethod
    async def execute(self, project_id: UUID, *args, **kwargs) -> Dict[str, Any]:
        pass
