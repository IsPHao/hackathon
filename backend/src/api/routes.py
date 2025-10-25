from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from uuid import UUID, uuid4
from datetime import datetime
import logging
from typing import Dict, Any

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


async def process_novel_task(
    task_id: UUID,
    novel_text: str,
    mode: str,
    options: Dict[str, Any] = None
):
    try:
        await progress_tracker.initialize(task_id)
        
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
        
        task_results[str(task_id)] = {
            "status": "completed",
            "result": result
        }
        
        await progress_tracker.update(
            project_id=task_id,
            stage="completed",
            progress=100,
            message="小说解析完成",
            result=result
        )
        
        logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}", exc_info=True)
        
        task_results[str(task_id)] = {
            "status": "failed",
            "error": str(e)
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
    request: NovelUploadRequest,
    background_tasks: BackgroundTasks
):
    try:
        task_id = uuid4()
        
        task_results[str(task_id)] = {
            "status": "processing"
        }
        
        background_tasks.add_task(
            process_novel_task,
            task_id=task_id,
            novel_text=request.novel_text,
            mode=request.mode,
            options=request.options
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
