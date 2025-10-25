# Core 模块设计文档

## 1. 模块概述

Core模块是系统的核心业务编排层，负责协调各个Agent的工作流程，管理任务状态，处理错误和重试。

### 1.1 职责
- Agent工作流编排

### 1.2 设计原则
- 单一职责：每个类只负责一个特定功能
- 开闭原则：对扩展开放，对修改关闭
- 依赖倒置：依赖抽象而非具体实现
- 可测试性：所有组件可独立测试

## 2. 目录结构

```
core/
├── __init__.py
├── pipeline.py          # 主工作流编排器
```

## 3. 核心类设计

### 3.1 AnimePipeline (主工作流编排器)

负责整个视频生成的工作流编排。

```python
from typing import Dict, Any, Optional
from uuid import UUID
import asyncio

class AnimePipeline:
    """
    动漫生成主工作流编排器
    
    职责:
    - 协调各个Agent的执行顺序
    - 管理Agent之间的数据流转
    - 处理工作流级别的错误
    - 上报整体进度
    """
    
    def __init__(
        self,
        novel_parser: NovelParserAgent,
        storyboard: StoryboardAgent,
        character_consistency: CharacterConsistencyAgent,
        image_generator: ImageGeneratorAgent,
        voice_synthesizer: VoiceSynthesizerAgent,
        video_composer: VideoComposerAgent,
        progress_tracker: ProgressTracker,
        error_handler: ErrorHandler
    ):
        self.novel_parser = novel_parser
        self.storyboard = storyboard
        self.character_consistency = character_consistency
        self.image_generator = image_generator
        self.voice_synthesizer = voice_synthesizer
        self.video_composer = video_composer
        self.progress_tracker = progress_tracker
        self.error_handler = error_handler
    
    async def execute(
        self,
        project_id: UUID,
        novel_text: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行完整的动漫生成流程
        
        Args:
            project_id: 项目ID
            novel_text: 小说文本
            options: 可选配置
        
        Returns:
            Dict: 生成结果，包含video_url等信息
        
        Raises:
            PipelineError: 工作流执行失败
        """
        try:
            # 初始化进度跟踪
            await self.progress_tracker.initialize(project_id)
            
            # 阶段1: 小说解析 (0-15%)
            await self.progress_tracker.update(
                project_id, "novel_parsing", 0, "开始解析小说..."
            )
            novel_data = await self._execute_with_retry(
                self.novel_parser.parse,
                novel_text
            )
            await self.progress_tracker.update(
                project_id, "novel_parsing", 15, "小说解析完成"
            )
            
            # 阶段2: 分镜设计 (15-30%)
            await self.progress_tracker.update(
                project_id, "storyboarding", 15, "开始分镜设计..."
            )
            storyboard_data = await self._execute_with_retry(
                self.storyboard.create,
                novel_data
            )
            await self.progress_tracker.update(
                project_id, "storyboarding", 30, "分镜设计完成"
            )
            
            # 阶段3: 角色一致性管理 (30-40%)
            await self.progress_tracker.update(
                project_id, "character_management", 30, "管理角色一致性..."
            )
            character_data = await self._execute_with_retry(
                self.character_consistency.manage,
                novel_data.characters,
                project_id
            )
            await self.progress_tracker.update(
                project_id, "character_management", 40, "角色管理完成"
            )
            
            # 阶段4: 并行生成图片和音频 (40-80%)
            await self.progress_tracker.update(
                project_id, "content_generation", 40, "开始生成内容..."
            )
            
            images, audios = await asyncio.gather(
                self._generate_images_with_progress(
                    project_id, storyboard_data, character_data
                ),
                self._generate_audios_with_progress(
                    project_id, storyboard_data
                )
            )
            
            await self.progress_tracker.update(
                project_id, "content_generation", 80, "内容生成完成"
            )
            
            # 阶段5: 视频合成 (80-100%)
            await self.progress_tracker.update(
                project_id, "video_composition", 80, "开始合成视频..."
            )
            video = await self._execute_with_retry(
                self.video_composer.compose,
                images,
                audios,
                storyboard_data
            )
            await self.progress_tracker.update(
                project_id, "video_composition", 100, "视频合成完成"
            )
            
            # 完成
            await self.progress_tracker.complete(
                project_id, video_url=video.url
            )
            
            return {
                "video_url": video.url,
                "thumbnail_url": video.thumbnail_url,
                "duration": video.duration,
                "scenes_count": len(storyboard_data.scenes)
            }
        
        except Exception as e:
            # 错误处理
            await self.progress_tracker.fail(project_id, str(e))
            await self.error_handler.handle(project_id, e)
            raise PipelineError(f"Pipeline execution failed: {e}") from e
    
    async def _execute_with_retry(
        self,
        func,
        *args,
        max_retries: int = 3,
        **kwargs
    ):
        """
        带重试机制的执行
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            max_retries: 最大重试次数
            **kwargs: 关键字参数
        
        Returns:
            函数执行结果
        
        Raises:
            Exception: 重试失败后抛出最后一次异常
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} attempts failed")
        
        raise last_exception
    
    async def _generate_images_with_progress(
        self,
        project_id: UUID,
        storyboard_data: Any,
        character_data: Any
    ) -> List[str]:
        """
        生成图片并上报进度
        
        Args:
            project_id: 项目ID
            storyboard_data: 分镜数据
            character_data: 角色数据
        
        Returns:
            List[str]: 图片URL列表
        """
        total_scenes = len(storyboard_data.scenes)
        images = []
        
        for i, scene in enumerate(storyboard_data.scenes):
            image_url = await self._execute_with_retry(
                self.image_generator.generate,
                scene,
                character_data
            )
            images.append(image_url)
            
            # 更新进度 (40-70%)
            progress = 40 + int((i + 1) / total_scenes * 30)
            await self.progress_tracker.update(
                project_id,
                "content_generation",
                progress,
                f"已生成 {i + 1}/{total_scenes} 个场景图片"
            )
        
        return images
    
    async def _generate_audios_with_progress(
        self,
        project_id: UUID,
        storyboard_data: Any
    ) -> List[str]:
        """
        生成音频并上报进度
        
        Args:
            project_id: 项目ID
            storyboard_data: 分镜数据
        
        Returns:
            List[str]: 音频URL列表
        """
        total_scenes = len(storyboard_data.scenes)
        audios = []
        
        for i, scene in enumerate(storyboard_data.scenes):
            audio_url = await self._execute_with_retry(
                self.voice_synthesizer.synthesize,
                scene.dialogue,
                scene.character
            )
            audios.append(audio_url)
            
            # 更新进度 (70-80%)
            progress = 70 + int((i + 1) / total_scenes * 10)
            await self.progress_tracker.update(
                project_id,
                "content_generation",
                progress,
                f"已生成 {i + 1}/{total_scenes} 个场景音频"
            )
        
        return audios
```

### 3.2 TaskManager (任务管理器)

管理异步任务的生命周期。

```python
from typing import Dict, Optional, Callable
from uuid import UUID
import asyncio
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Task:
    """任务对象"""
    
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
        """执行任务"""
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
    
    职责:
    - 创建和管理异步任务
    - 跟踪任务状态
    - 取消任务
    - 清理完成的任务
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
        """
        创建新任务
        
        Args:
            task_id: 任务ID
            project_id: 项目ID
            task_type: 任务类型
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            Task: 创建的任务对象
        """
        task = Task(task_id, project_id, task_type, func, *args, **kwargs)
        self.tasks[task_id] = task
        
        # 创建asyncio任务
        task.asyncio_task = asyncio.create_task(task.execute())
        
        return task
    
    def get_task(self, task_id: UUID) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    async def cancel_task(self, task_id: UUID) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 是否成功取消
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
            task_id: 任务ID
            timeout: 超时时间(秒)
        
        Returns:
            任务结果
        
        Raises:
            TimeoutError: 超时
            Exception: 任务执行失败
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
        
        Args:
            max_age_seconds: 最大保留时间(秒)
        """
        # 实现定期清理逻辑
        pass
```

### 3.3 ProgressTracker (进度跟踪器)

跟踪和上报任务进度。

```python
from typing import Dict, Any, Optional
from uuid import UUID
import asyncio
import json
import aioredis

class ProgressTracker:
    """
    进度跟踪器
    
    职责:
    - 跟踪任务进度
    - 通过Redis发布进度更新
    - 支持WebSocket实时推送
    """
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
    
    async def initialize(self, project_id: UUID):
        """
        初始化项目进度
        
        Args:
            project_id: 项目ID
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
        更新进度
        
        Args:
            project_id: 项目ID
            stage: 当前阶段
            progress: 进度(0-100)
            message: 进度消息
            **extra: 额外信息
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
        标记完成
        
        Args:
            project_id: 项目ID
            video_url: 视频URL
            **extra: 额外信息
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
        标记失败
        
        Args:
            project_id: 项目ID
            error: 错误信息
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
        获取当前进度
        
        Args:
            project_id: 项目ID
        
        Returns:
            Dict: 进度数据
        """
        key = f"progress:{project_id}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def _publish_progress(self, project_id: UUID, progress_data: Dict[str, Any]):
        """发布进度到Redis频道"""
        channel = f"project:{project_id}:progress"
        await self.redis.publish(channel, json.dumps(progress_data))
    
    async def _save_progress(self, project_id: UUID, progress_data: Dict[str, Any]):
        """保存进度到Redis"""
        key = f"progress:{project_id}"
        await self.redis.setex(
            key,
            3600,  # 1小时过期
            json.dumps(progress_data)
        )
```

### 3.4 ErrorHandler (错误处理器)

统一的错误处理。

```python
from typing import Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class ErrorHandler:
    """
    错误处理器
    
    职责:
    - 捕获和记录错误
    - 错误分类
    - 错误上报
    - 错误恢复策略
    """
    
    async def handle(
        self,
        project_id: UUID,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        处理错误
        
        Args:
            project_id: 项目ID
            error: 异常对象
            context: 上下文信息
        """
        # 记录错误
        logger.error(
            f"Error in project {project_id}: {error}",
            exc_info=True,
            extra=context or {}
        )
        
        # 错误分类
        error_type = self._classify_error(error)
        
        # 上报错误 (例如发送到Sentry)
        await self._report_error(project_id, error, error_type, context)
        
        # 尝试恢复 (如果可能)
        if self._is_recoverable(error_type):
            await self._attempt_recovery(project_id, error, context)
    
    def _classify_error(self, error: Exception) -> str:
        """错误分类"""
        if isinstance(error, APIError):
            return "api_error"
        elif isinstance(error, ValidationError):
            return "validation_error"
        elif isinstance(error, TimeoutError):
            return "timeout_error"
        else:
            return "unknown_error"
    
    async def _report_error(
        self,
        project_id: UUID,
        error: Exception,
        error_type: str,
        context: Optional[Dict[str, Any]]
    ):
        """上报错误到监控系统"""
        # 集成Sentry等错误追踪系统
        pass
    
    def _is_recoverable(self, error_type: str) -> bool:
        """判断错误是否可恢复"""
        return error_type in ["api_error", "timeout_error"]
    
    async def _attempt_recovery(
        self,
        project_id: UUID,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ):
        """尝试从错误中恢复"""
        # 实现恢复逻辑
        pass
```

## 4. 接口定义

```python
# interfaces.py

from abc import ABC, abstractmethod
from typing import Any, Dict

class Agent(ABC):
    """Agent基类"""
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """执行Agent逻辑"""
        pass

class Pipeline(ABC):
    """Pipeline基类"""
    
    @abstractmethod
    async def execute(self, project_id: UUID, *args, **kwargs) -> Dict[str, Any]:
        """执行Pipeline"""
        pass
```

## 5. 异常定义

```python
class PipelineError(Exception):
    """Pipeline执行错误"""
    pass

class AgentError(Exception):
    """Agent执行错误"""
    pass

class RetryExhaustedError(Exception):
    """重试次数用尽"""
    pass

class ValidationError(Exception):
    """数据验证错误"""
    pass

class APIError(Exception):
    """API调用错误"""
    pass
```

## 6. 配置管理

```python
from pydantic import BaseSettings

class CoreSettings(BaseSettings):
    """Core模块配置"""
    
    max_retries: int = 3
    retry_backoff_base: int = 2
    task_timeout: int = 3600
    cleanup_interval: int = 3600
    
    class Config:
        env_prefix = "CORE_"
```

## 7. 使用示例

```python
# 初始化
pipeline = AnimePipeline(
    novel_parser=NovelParserAgent(),
    storyboard=StoryboardAgent(),
    character_consistency=CharacterConsistencyAgent(),
    image_generator=ImageGeneratorAgent(),
    voice_synthesizer=VoiceSynthesizerAgent(),
    video_composer=VideoComposerAgent(),
    progress_tracker=ProgressTracker(redis_client),
    error_handler=ErrorHandler()
)

# 执行
result = await pipeline.execute(
    project_id=project_id,
    novel_text=novel_text,
    options={"style": "anime", "quality": "high"}
)

print(f"Video URL: {result['video_url']}")
```

## 8. 测试策略

```python
# tests/test_pipeline.py

import pytest
from unittest.mock import AsyncMock, Mock

@pytest.mark.asyncio
async def test_pipeline_execute_success():
    # Mock agents
    novel_parser = AsyncMock()
    storyboard = AsyncMock()
    # ... 其他agents
    
    pipeline = AnimePipeline(
        novel_parser=novel_parser,
        # ...
    )
    
    result = await pipeline.execute(
        project_id=test_project_id,
        novel_text="test novel"
    )
    
    assert result["video_url"] is not None
    novel_parser.parse.assert_called_once()
```

## 9. 性能优化

- 使用asyncio并发执行独立任务
- 合理使用缓存减少重复计算
- 连接池管理数据库和Redis连接
- 批量处理减少网络请求

## 10. 监控指标

- Pipeline执行时长
- 各阶段耗时分布
- 错误率和重试次数
- 并发任务数
