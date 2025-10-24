from typing import Dict, Any, Optional
from uuid import UUID
import json
import logging
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    进度跟踪器
    
    负责跟踪任务执行进度，优先使用内存存储，可选Redis进行分布式进度共享。
    如果Redis不可用，自动降级为内存存储模式。
    
    Attributes:
        redis: Redis客户端实例（可选），用于发布/存储进度数据
        _memory_storage: 内存存储，存储进度数据
        _lock: 异步锁，保证内存存储的线程安全
        _use_redis: 是否使用Redis
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._memory_storage: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._use_redis = redis_client is not None
    
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
        
        优先从内存获取，如果启用了Redis也会尝试从Redis获取。
        
        Args:
            project_id: 项目ID
        
        Returns:
            Optional[Dict[str, Any]]: 进度数据，不存在时返回None
        """
        key = str(project_id)
        
        async with self._lock:
            if key in self._memory_storage:
                return self._memory_storage[key]
        
        if self._use_redis:
            try:
                redis_key = f"progress:{project_id}"
                data = await self.redis.get(redis_key)
                if data:
                    progress_data = json.loads(data)
                    async with self._lock:
                        self._memory_storage[key] = progress_data
                    return progress_data
            except Exception as e:
                logger.warning(f"Failed to get progress from Redis: {e}")
        
        return None
    
    async def _publish_progress(self, project_id: UUID, progress_data: Dict[str, Any]):
        """
        发布进度到Redis频道
        
        如果Redis不可用，仅记录到日志。
        
        Args:
            project_id: 项目ID
            progress_data: 进度数据
        """
        logger.info(f"Progress: {progress_data}")
        
        if not self._use_redis:
            return
        
        try:
            channel = f"project:{project_id}:progress"
            await self.redis.publish(channel, json.dumps(progress_data))
        except Exception as e:
            logger.warning(f"Failed to publish progress to Redis: {e}, using memory storage only")
            self._use_redis = False
    
    async def _save_progress(self, project_id: UUID, progress_data: Dict[str, Any]):
        """
        保存进度到内存和Redis（如果可用）
        
        优先保存到内存，然后尝试保存到Redis。
        Redis保存失败不影响内存存储。
        
        Args:
            project_id: 项目ID
            progress_data: 进度数据
        """
        key = str(project_id)
        
        async with self._lock:
            self._memory_storage[key] = progress_data
        
        if not self._use_redis:
            return
        
        try:
            redis_key = f"progress:{project_id}"
            await self.redis.setex(
                redis_key,
                3600,
                json.dumps(progress_data)
            )
        except Exception as e:
            logger.warning(f"Failed to save progress to Redis: {e}, using memory storage only")
            self._use_redis = False
