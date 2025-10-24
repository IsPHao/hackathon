from typing import Dict, Any, Optional
from uuid import UUID
import json
import logging

logger = logging.getLogger(__name__)


class ProgressTracker:
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
    
    async def initialize(self, project_id: UUID):
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
        progress_data = {
            "type": "error",
            "project_id": str(project_id),
            "status": "failed",
            "error": error
        }
        
        await self._publish_progress(project_id, progress_data)
        await self._save_progress(project_id, progress_data)
    
    async def get_progress(self, project_id: UUID) -> Optional[Dict[str, Any]]:
        if not self.redis:
            return None
        
        key = f"progress:{project_id}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def _publish_progress(self, project_id: UUID, progress_data: Dict[str, Any]):
        if not self.redis:
            logger.info(f"Progress: {progress_data}")
            return
        
        channel = f"project:{project_id}:progress"
        await self.redis.publish(channel, json.dumps(progress_data))
    
    async def _save_progress(self, project_id: UUID, progress_data: Dict[str, Any]):
        if not self.redis:
            return
        
        key = f"progress:{project_id}"
        await self.redis.setex(
            key,
            3600,
            json.dumps(progress_data)
        )
