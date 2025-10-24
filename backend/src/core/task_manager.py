from typing import Dict, Optional, Callable
from uuid import UUID
import asyncio
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    
    def __init__(
        self,
        task_id: UUID,
        project_id: UUID,
        task_type: str,
        func: Callable,
        *args,
        **kwargs
    ):
        self.task_id = task_id
        self.project_id = project_id
        self.task_type = task_type
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.asyncio_task: Optional[asyncio.Task] = None
    
    async def execute(self):
        self.status = TaskStatus.RUNNING
        try:
            self.result = await self.func(*self.args, **self.kwargs)
            self.status = TaskStatus.COMPLETED
        except Exception as e:
            self.error = e
            self.status = TaskStatus.FAILED
            raise


class TaskManager:
    
    def __init__(self):
        self.tasks: Dict[UUID, Task] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def create_task(
        self,
        task_id: UUID,
        project_id: UUID,
        task_type: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Task:
        task = Task(task_id, project_id, task_type, func, *args, **kwargs)
        self.tasks[task_id] = task
        
        task.asyncio_task = asyncio.create_task(task.execute())
        
        return task
    
    def get_task(self, task_id: UUID) -> Optional[Task]:
        return self.tasks.get(task_id)
    
    async def cancel_task(self, task_id: UUID) -> bool:
        task = self.tasks.get(task_id)
        if task and task.asyncio_task:
            task.asyncio_task.cancel()
            task.status = TaskStatus.CANCELLED
            return True
        return False
    
    async def wait_for_task(self, task_id: UUID, timeout: Optional[float] = None):
        task = self.tasks.get(task_id)
        if not task or not task.asyncio_task:
            raise ValueError(f"Task {task_id} not found")
        
        try:
            await asyncio.wait_for(task.asyncio_task, timeout=timeout)
            return task.result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Task {task_id} timed out")
    
    async def cleanup_completed_tasks(self, max_age_seconds: int = 3600):
        pass
