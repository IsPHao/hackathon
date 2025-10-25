from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class NovelUploadRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "novel_text": "这是一个关于勇者的故事...",
                "mode": "enhanced",
                "options": {
                    "max_characters": 10,
                    "max_scenes": 30
                }
            }
        }
    )
    
    novel_text: str = Field(..., min_length=100, max_length=100000, description="小说文本内容")
    mode: str = Field(default="enhanced", pattern="^(simple|enhanced)$", description="解析模式: simple或enhanced")
    options: Optional[Dict[str, Any]] = Field(default=None, description="额外配置选项")


class NovelUploadResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "processing",
                "message": "小说上传成功,正在处理中...",
                "created_at": "2024-10-24T12:00:00Z"
            }
        }
    )
    
    task_id: UUID = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="提示信息")
    created_at: datetime = Field(..., description="创建时间")


class ProgressResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "processing",
                "stage": "novel_parsing",
                "progress": 45,
                "message": "正在解析小说文本...",
                "result": None,
                "error": None
            }
        }
    )
    
    task_id: UUID = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: processing/completed/failed")
    stage: Optional[str] = Field(None, description="当前处理阶段")
    progress: int = Field(..., ge=0, le=100, description="进度百分比 (0-100)")
    message: str = Field(..., description="进度描述")
    result: Optional[Dict[str, Any]] = Field(None, description="处理结果(完成时)")
    error: Optional[str] = Field(None, description="错误信息(失败时)")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="错误信息")
    details: Optional[str] = Field(None, description="错误详情")
    error_code: Optional[str] = Field(None, description="错误代码")
