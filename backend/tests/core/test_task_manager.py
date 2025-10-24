import pytest
import asyncio
from uuid import uuid4

from backend.src.core.task_manager import TaskManager, Task, TaskStatus


@pytest.fixture
def task_manager():
    return TaskManager()


@pytest.mark.asyncio
async def test_create_task(task_manager):
    task_id = uuid4()
    project_id = uuid4()
    
    async def sample_func():
        await asyncio.sleep(0.1)
        return "result"
    
    task = await task_manager.create_task(
        task_id=task_id,
        project_id=project_id,
        task_type="test_task",
        func=sample_func
    )
    
    assert task.task_id == task_id
    assert task.project_id == project_id
    assert task.task_type == "test_task"
    assert task.asyncio_task is not None


@pytest.mark.asyncio
async def test_get_task(task_manager):
    task_id = uuid4()
    project_id = uuid4()
    
    async def sample_func():
        return "result"
    
    await task_manager.create_task(
        task_id=task_id,
        project_id=project_id,
        task_type="test_task",
        func=sample_func
    )
    
    retrieved_task = task_manager.get_task(task_id)
    assert retrieved_task is not None
    assert retrieved_task.task_id == task_id


@pytest.mark.asyncio
async def test_task_execution_success(task_manager):
    task_id = uuid4()
    project_id = uuid4()
    
    async def sample_func():
        await asyncio.sleep(0.1)
        return "success"
    
    task = await task_manager.create_task(
        task_id=task_id,
        project_id=project_id,
        task_type="test_task",
        func=sample_func
    )
    
    result = await task_manager.wait_for_task(task_id, timeout=1.0)
    
    assert result == "success"
    assert task.status == TaskStatus.COMPLETED
    assert task.result == "success"


@pytest.mark.asyncio
async def test_task_execution_failure(task_manager):
    task_id = uuid4()
    project_id = uuid4()
    
    async def failing_func():
        raise ValueError("Test error")
    
    task = await task_manager.create_task(
        task_id=task_id,
        project_id=project_id,
        task_type="test_task",
        func=failing_func
    )
    
    with pytest.raises(ValueError, match="Test error"):
        await task_manager.wait_for_task(task_id, timeout=1.0)
    
    assert task.status == TaskStatus.FAILED
    assert isinstance(task.error, ValueError)


@pytest.mark.asyncio
async def test_cancel_task(task_manager):
    task_id = uuid4()
    project_id = uuid4()
    
    async def long_running_func():
        await asyncio.sleep(10)
        return "result"
    
    await task_manager.create_task(
        task_id=task_id,
        project_id=project_id,
        task_type="test_task",
        func=long_running_func
    )
    
    await asyncio.sleep(0.1)
    
    success = await task_manager.cancel_task(task_id)
    assert success is True
    
    task = task_manager.get_task(task_id)
    assert task.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_wait_for_nonexistent_task(task_manager):
    task_id = uuid4()
    
    with pytest.raises(ValueError, match="Task .* not found"):
        await task_manager.wait_for_task(task_id)


@pytest.mark.asyncio
async def test_wait_for_task_timeout(task_manager):
    task_id = uuid4()
    project_id = uuid4()
    
    async def long_running_func():
        await asyncio.sleep(5)
        return "result"
    
    await task_manager.create_task(
        task_id=task_id,
        project_id=project_id,
        task_type="test_task",
        func=long_running_func
    )
    
    with pytest.raises(TimeoutError):
        await task_manager.wait_for_task(task_id, timeout=0.1)
