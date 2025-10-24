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
    """
    异步任务封装类
    
    封装了异步函数的执行、状态跟踪和结果存储。
    
    Attributes:
        task_id: 任务唯一标识符
        project_id: 所属项目ID
        task_type: 任务类型（如'image_generation', 'video_composition'）
        func: 要执行的异步函数
        args: 函数的位置参数
        kwargs: 函数的关键字参数
        status: 当前任务状态
        result: 任务执行结果
        error: 任务执行错误（如果失败）
        asyncio_task: 底层asyncio.Task对象
    """
    
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
        """
        执行任务并更新状态
        
        将任务状态设为RUNNING，执行函数，然后根据结果设为COMPLETED或FAILED。
        
        Raises:
            Exception: 任务执行失败时抛出异常
        """
        self.status = TaskStatus.RUNNING
        try:
            self.result = await self.func(*self.args, **self.kwargs)
            self.status = TaskStatus.COMPLETED
        except Exception as e:
            self.error = e
            self.status = TaskStatus.FAILED
            raise


class TaskManager:
    """
    任务管理器
    
    负责创建、跟踪和管理异步任务的生命周期。
    支持任务创建、查询、取消和清理。
    
    Attributes:
        tasks: 任务字典，键为任务ID，值为Task对象
        _cleanup_task: 定期清理任务的asyncio.Task
    """
    
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
        """
        根据ID获取任务
        
        Args:
            task_id: 任务唯一标识符
        
        Returns:
            Optional[Task]: 任务对象，如果不存在则返回None
        """
        return self.tasks.get(task_id)
    
    async def cancel_task(self, task_id: UUID) -> bool:
        """
        取消正在运行的任务
        
        Args:
            task_id: 要取消的任务ID
        
        Returns:
            bool: 如果成功取消返回True，否则返回False
        """
        task = self.tasks.get(task_id)
        if task and task.asyncio_task:
            task.asyncio_task.cancel()
            task.status = TaskStatus.CANCELLED
            return True
        return False
    
    async def wait_for_task(self, task_id: UUID, timeout: Optional[float] = None):
        """
        等待任务完成
        
        Args:
            task_id: 要等待的任务ID
            timeout: 超时时间（秒），None表示不超时
        
        Returns:
            任务的执行结果
        
        Raises:
            ValueError: 任务不存在
            TimeoutError: 等待超时
        """
        task = self.tasks.get(task_id)
        if not task or not task.asyncio_task:
            raise ValueError(f"Task {task_id} not found")
        
        try:
            await asyncio.wait_for(task.asyncio_task, timeout=timeout)
            return task.result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Task {task_id} timed out")
    
    async def cleanup_completed_tasks(self, max_age_seconds: int = 3600):
        """
        清理已完成的任务
        
        删除状态为COMPLETED、FAILED或CANCELLED的任务，释放内存。
        注：当前实现删除所有已结束的任务，未来版本将支持基于时间的清理。
        
        Args:
            max_age_seconds: 最大保留时间（秒），当前未使用
        """
        completed_task_ids = [
            task_id for task_id, task in self.tasks.items()
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]
        
        for task_id in completed_task_ids:
            del self.tasks[task_id]
        
        if completed_task_ids:
            logger.info(f"Cleaned up {len(completed_task_ids)} completed tasks")
