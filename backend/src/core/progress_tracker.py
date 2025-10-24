from typing import Dict, Any, Optional
from uuid import UUID
import json
import logging

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    进度跟踪器
    
    负责跟踪任务执行进度，通过Redis发布进度更新，支持WebSocket实时推送。
    如果Redis不可用，将降级为日志记录模式。
    
    Attributes:
        redis: Redis客户端实例，用于发布/存储进度数据
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
    
    async def initialize(self, project_id: UUID):
        """
        初始化项目进度
        
        创建初始进度状态并发布到Redis。
        
        Args:
            project_id: 项目唯一标识符
        """
        progress_data = {
            "project_id": str(project_id),
            "status": "processing",
            "stage": "initializing",
            "progress": 0,
            "message": "初始化中..."
        }
        
        await self._publish_progress(project_id, progress_data)
        await self._save_progress(project_id, progress_data)
    
    async def update(
        self,
        project_id: UUID,
        stage: str,
        progress: int,
        message: str,
        **extra
    ):
        """
        更新项目进度
        
        Args:
            project_id: 项目ID
            stage: 当前阶段（如'novel_parsing', 'image_generation'）
            progress: 进度百分比（0-100）
            message: 进度消息描述
            **extra: 额外的进度信息
        """
        progress_data = {
            "type": "progress",
            "project_id": str(project_id),
            "status": "processing",
            "stage": stage,
            "progress": progress,
            "message": message,
            **extra
        }
        
        await self._publish_progress(project_id, progress_data)
        await self._save_progress(project_id, progress_data)
    
    async def complete(
        self,
        project_id: UUID,
        video_url: str,
        **extra
    ):
        """
        标记项目完成
        
        Args:
            project_id: 项目ID
            video_url: 生成的视频URL
            **extra: 额外的完成信息
        """
        progress_data = {
            "type": "completed",
            "project_id": str(project_id),
            "status": "completed",
            "progress": 100,
            "message": "视频生成完成",
            "video_url": video_url,
            **extra
        }
        
        await self._publish_progress(project_id, progress_data)
        await self._save_progress(project_id, progress_data)
    
    async def fail(
        self,
        project_id: UUID,
        error: str
    ):
        """
        标记项目失败
        
        Args:
            project_id: 项目ID
            error: 错误信息描述
        """
        progress_data = {
            "type": "error",
            "project_id": str(project_id),
            "status": "failed",
            "error": error
        }
        
        await self._publish_progress(project_id, progress_data)
        await self._save_progress(project_id, progress_data)
    
    async def get_progress(self, project_id: UUID) -> Optional[Dict[str, Any]]:
        """
        获取项目当前进度
        
        Args:
            project_id: 项目ID
        
        Returns:
            Optional[Dict[str, Any]]: 进度数据，如果不存在或Redis不可用则返回None
        """
        if not self.redis:
            return None
        
        key = f"progress:{project_id}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def _publish_progress(self, project_id: UUID, progress_data: Dict[str, Any]):
        """
        发布进度到Redis频道
        
        如果Redis不可用，将进度记录到日志。
        
        Args:
            project_id: 项目ID
            progress_data: 进度数据
        """
        if not self.redis:
            logger.info(f"Progress: {progress_data}")
            return
        
        try:
            channel = f"project:{project_id}:progress"
            await self.redis.publish(channel, json.dumps(progress_data))
        except Exception as e:
            logger.error(f"Failed to publish progress to Redis: {e}")
            logger.info(f"Progress (fallback): {progress_data}")
    
    async def _save_progress(self, project_id: UUID, progress_data: Dict[str, Any]):
        """
        保存进度到Redis
        
        使用SETEX命令保存带过期时间的进度数据（1小时）。
        
        Args:
            project_id: 项目ID
            progress_data: 进度数据
        """
        if not self.redis:
            return
        
        try:
            key = f"progress:{project_id}"
            await self.redis.setex(
                key,
                3600,
                json.dumps(progress_data)
            )
        except Exception as e:
            logger.error(f"Failed to save progress to Redis: {e}")
