from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect
from uuid import UUID, uuid4
from datetime import datetime
import logging
import asyncio
from typing import Dict, Any, Optional

from .schemas import (
    NovelUploadRequest,
    NovelUploadResponse,
    ProgressResponse,
    ErrorResponse
)
from ..core.progress_tracker import ProgressTracker
from ..agents.novel_parser import NovelParserAgent
from ..core.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/novels", tags=["novels"])

progress_tracker = ProgressTracker()

task_results: Dict[str, Dict[str, Any]] = {}
_task_results_lock: Optional[asyncio.Lock] = None
TASK_TTL_SECONDS = 3600


def get_task_results_lock() -> asyncio.Lock:
    """
    获取任务结果锁，延迟初始化以避免事件循环绑定问题
    """
    global _task_results_lock
    if _task_results_lock is None:
        _task_results_lock = asyncio.Lock()
    return _task_results_lock


async def _cleanup_old_tasks():
    """
    清理超过TTL的已完成或失败任务
    """
    try:
        current_time = datetime.utcnow()
        async with get_task_results_lock():
            tasks_to_remove = []
            for task_id, task_data in task_results.items():
                completed_at = task_data.get("completed_at")
                if completed_at:
                    age_seconds = (current_time - completed_at).total_seconds()
                    if age_seconds > TASK_TTL_SECONDS:
                        tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del task_results[task_id]
                logger.info(f"Cleaned up old task: {task_id}")
    except Exception as e:
        logger.error(f"Error cleaning up old tasks: {e}", exc_info=True)


async def process_novel_task(
    task_id: UUID,
    novel_text: str,
    mode: str,
    options: Dict[str, Any] = None
):
    try:
        
        await progress_tracker.update(
            project_id=task_id,
            stage="novel_parsing",
            progress=10,
            message="开始解析小说..."
        )
        
        llm = LLMFactory.create_llm()
        agent = NovelParserAgent(llm=llm)
        
        await progress_tracker.update(
            project_id=task_id,
            stage="novel_parsing",
            progress=30,
            message="正在解析小说内容..."
        )
        
        result = await agent.parse(
            novel_text=novel_text,
            mode=mode,
            options=options
        )
        
        await progress_tracker.update(
            project_id=task_id,
            stage="novel_parsing",
            progress=90,
            message="解析完成，正在保存结果..."
        )
        
        async with get_task_results_lock():
            task_results[str(task_id)] = {
                "status": "completed",
                "result": result,
                "completed_at": datetime.utcnow()
            }
        
        await progress_tracker.complete(
            project_id=task_id,
            message="小说解析完成",
            result=result
        )
        
        logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}", exc_info=True)
        
        async with get_task_results_lock():
            task_results[str(task_id)] = {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.utcnow()
            }
        
        await progress_tracker.fail(
            project_id=task_id,
            error=str(e)
        )


@router.post(
    "/upload",
    response_model=NovelUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="上传小说文本",
    description="上传小说文本并开始异步处理，返回任务ID用于查询进度"
)
async def upload_novel(
    request: NovelUploadRequest
):
    try:
        task_id = uuid4()
        
        await progress_tracker.initialize(task_id)
        
        async with get_task_results_lock():
            task_results[str(task_id)] = {
                "status": "processing",
                "created_at": datetime.utcnow()
            }
        
        asyncio.create_task(_cleanup_old_tasks())
        
        asyncio.create_task(
            process_novel_task(
                task_id=task_id,
                novel_text=request.novel_text,
                mode=request.mode,
                options=request.options
            )
        )
        
        logger.info(f"Created novel processing task: {task_id}")
        
        return NovelUploadResponse(
            task_id=task_id,
            status="processing",
            message="小说上传成功,正在处理中...",
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to create task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建任务失败: {str(e)}"
        )


@router.get(
    "/{task_id}/progress",
    response_model=ProgressResponse,
    summary="查询处理进度",
    description="根据任务ID查询小说处理进度"
)
async def get_progress(task_id: UUID):
    try:
        progress_data = await progress_tracker.get_progress(task_id)
        
        if not progress_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务 {task_id} 不存在"
            )
        
        async with get_task_results_lock():
            task_result = task_results.get(str(task_id), {})
        
        return ProgressResponse(
            task_id=task_id,
            status=progress_data.get("status", "processing"),
            stage=progress_data.get("stage"),
            progress=progress_data.get("progress", 0),
            message=progress_data.get("message", ""),
            result=task_result.get("result") if progress_data.get("status") == "completed" else None,
            error=progress_data.get("error")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get progress for task {task_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询进度失败: {str(e)}"
        )


@router.websocket("/{task_id}/ws")
async def websocket_progress(websocket: WebSocket, task_id: UUID):
    """
    WebSocket 实时进度推送
    
    建立WebSocket连接后，服务器会实时推送任务进度更新。
    
    消息格式:
    ```json
    {
        "type": "progress",
        "project_id": "task-id",
        "status": "processing",
        "stage": "novel_parsing",
        "progress": 50,
        "message": "正在解析小说文本..."
    }
    ```
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for task {task_id}")
    
    try:
        await progress_tracker.add_websocket_connection(task_id, websocket)
        
        current_progress = await progress_tracker.get_progress(task_id)
        if current_progress:
            import json
            await websocket.send_text(json.dumps(current_progress))
        
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received from client: {data}")
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for task {task_id}")
                break
            except Exception as e:
                logger.error(f"Error receiving WebSocket message: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {str(e)}", exc_info=True)
    finally:
        await progress_tracker.remove_websocket_connection(task_id, websocket)
        try:
            await websocket.close()
        except:
            pass
