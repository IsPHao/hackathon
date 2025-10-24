from typing import Dict, Any, Optional, List
from uuid import UUID
import asyncio
import logging

from .exceptions import PipelineError
from .progress_tracker import ProgressTracker
from .error_handler import ErrorHandler
from .config import CoreSettings

logger = logging.getLogger(__name__)


class AnimePipeline:
    """
    动漫生成主工作流编排器
    
    负责协调各个Agent的执行顺序，管理Agent之间的数据流转，
    处理工作流级别的错误，并上报整体进度。
    
    Attributes:
        novel_parser: 小说解析Agent
        storyboard: 分镜设计Agent
        character_consistency: 角色一致性管理Agent
        image_generator: 图像生成Agent
        voice_synthesizer: 语音合成Agent
        video_composer: 视频合成Agent
        progress_tracker: 进度跟踪器
        error_handler: 错误处理器
        config: 核心配置
    """
    
    def __init__(
        self,
        novel_parser,
        storyboard,
        character_consistency,
        image_generator,
        voice_synthesizer,
        video_composer,
        progress_tracker: ProgressTracker,
        error_handler: ErrorHandler,
        config: Optional[CoreSettings] = None,
        max_concurrent_generations: int = 5
    ):
        self.novel_parser = novel_parser
        self.storyboard = storyboard
        self.character_consistency = character_consistency
        self.image_generator = image_generator
        self.voice_synthesizer = voice_synthesizer
        self.video_composer = video_composer
        self.progress_tracker = progress_tracker
        self.error_handler = error_handler
        self.config = config or CoreSettings()
        self._generation_semaphore = asyncio.Semaphore(max_concurrent_generations)
        self._max_concurrent = max_concurrent_generations
    
    async def execute(
        self,
        project_id: UUID,
        novel_text: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行完整的动漫生成流程
        
        按照以下顺序执行各个Agent：
        1. 小说解析 (0-15%)
        2. 分镜设计 (15-30%)
        3. 角色一致性管理 (30-40%)
        4. 并行生成图片和音频 (40-80%)
        5. 视频合成 (80-100%)
        
        Args:
            project_id: 项目唯一标识符
            novel_text: 待处理的小说文本
            options: 可选配置参数，如风格、质量等
        
        Returns:
            Dict[str, Any]: 包含以下键的字典：
                - video_url: 生成的视频URL
                - thumbnail_url: 缩略图URL
                - duration: 视频时长（秒）
                - scenes_count: 场景数量
        
        Raises:
            PipelineError: 工作流执行失败时抛出，包含详细错误信息
        """
        try:
            await self.progress_tracker.initialize(project_id)
            
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
            
            await self.progress_tracker.update(
                project_id, "character_management", 30, "管理角色一致性..."
            )
            character_data = await self._execute_with_retry(
                self.character_consistency.manage,
                novel_data.get("characters", []),
                str(project_id)
            )
            await self.progress_tracker.update(
                project_id, "character_management", 40, "角色管理完成"
            )
            
            await self.progress_tracker.update(
                project_id, "content_generation", 40, "开始生成内容..."
            )
            
            images_task = self._generate_images_with_progress(
                project_id, storyboard_data, character_data
            )
            audios_task = self._generate_audios_with_progress(
                project_id, storyboard_data
            )
            
            images, audios = await asyncio.gather(images_task, audios_task)
            
            await self.progress_tracker.update(
                project_id, "content_generation", 80, "内容生成完成"
            )
            
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
            
            await self.progress_tracker.complete(
                project_id, video_url=video.get("url", "")
            )
            
            return {
                "video_url": video.get("url", ""),
                "thumbnail_url": video.get("thumbnail_url", ""),
                "duration": video.get("duration", 0),
                "scenes_count": len(storyboard_data.get("scenes", []))
            }
        
        except Exception as e:
            await self.progress_tracker.fail(project_id, str(e))
            await self.error_handler.handle(project_id, e)
            raise PipelineError(f"Pipeline execution failed: {e}") from e
    
    async def _execute_with_retry(
        self,
        func,
        *args,
        max_retries: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        带重试机制、超时和指数退避的异步函数执行
        
        当函数执行失败时，会按照指数退避策略进行重试。
        每次执行都有超时限制，防止永久挂起。
        等待时间计算公式：wait_time = retry_backoff_base ^ attempt
        
        Args:
            func: 要执行的异步函数
            *args: 函数的位置参数
            max_retries: 最大重试次数，默认使用配置中的值
            **kwargs: 函数的关键字参数
        
        Returns:
            Any: 函数执行的返回值
        
        Raises:
            Exception: 所有重试都失败后，抛出最后一次异常
            TimeoutError: 函数执行超时
        """
        from .exceptions import ValidationError
        
        max_retries = max_retries or self.config.max_retries
        timeout = self.config.task_timeout
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError as e:
                last_exception = TimeoutError(f"Function execution timed out after {timeout}s")
                if attempt < max_retries - 1:
                    wait_time = self.config.retry_backoff_base ** attempt
                    logger.warning(
                        f"Attempt {attempt + 1} timed out, retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} attempts failed due to timeout")
            except ValidationError as e:
                logger.error(f"Validation error, not retrying: {e}")
                raise
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = self.config.retry_backoff_base ** attempt
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
        storyboard_data: Dict[str, Any],
        character_data: Dict[str, Any]
    ) -> List[str]:
        """
        并发生成场景图片并实时上报进度
        
        使用信号量控制并发数，防止API率限制和资源耗尽。
        进度范围：40% -> 70%
        
        Args:
            project_id: 项目ID
            storyboard_data: 分镜数据，包含scenes列表
            character_data: 角色一致性数据
        
        Returns:
            List[str]: 生成的图片URL列表，顺序对应场景顺序
        """
        scenes = storyboard_data.get("scenes", [])
        total_scenes = len(scenes)
        
        async def generate_with_semaphore(i: int, scene: Dict[str, Any]) -> tuple[int, str]:
            async with self._generation_semaphore:
                image_url = await self._execute_with_retry(
                    self.image_generator.generate,
                    scene,
                    character_data,
                    str(project_id)
                )
                
                progress = 40 + int((i + 1) / total_scenes * 30)
                await self.progress_tracker.update(
                    project_id,
                    "content_generation",
                    progress,
                    f"已生成 {i + 1}/{total_scenes} 个场景图片"
                )
                
                return (i, image_url)
        
        tasks = [generate_with_semaphore(i, scene) for i, scene in enumerate(scenes)]
        results = await asyncio.gather(*tasks)
        
        results.sort(key=lambda x: x[0])
        images = [url for _, url in results]
        
        return images
    
    async def _generate_audios_with_progress(
        self,
        project_id: UUID,
        storyboard_data: Dict[str, Any]
    ) -> List[str]:
        """
        并发生成场景音频并实时上报进度
        
        使用信号量控制并发数，防止API率限制和资源耗尽。
        进度范围：70% -> 80%
        
        Args:
            project_id: 项目ID
            storyboard_data: 分镜数据，包含scenes列表
        
        Returns:
            List[str]: 生成的音频URL列表，顺序对应场景顺序
        """
        scenes = storyboard_data.get("scenes", [])
        total_scenes = len(scenes)
        
        async def synthesize_with_semaphore(i: int, scene: Dict[str, Any]) -> tuple[int, str]:
            async with self._generation_semaphore:
                audio_url = await self._execute_with_retry(
                    self.voice_synthesizer.synthesize,
                    scene,
                    str(project_id)
                )
                
                progress = 70 + int((i + 1) / total_scenes * 10)
                await self.progress_tracker.update(
                    project_id,
                    "content_generation",
                    progress,
                    f"已生成 {i + 1}/{total_scenes} 个场景音频"
                )
                
                return (i, audio_url)
        
        tasks = [synthesize_with_semaphore(i, scene) for i, scene in enumerate(scenes)]
        results = await asyncio.gather(*tasks)
        
        results.sort(key=lambda x: x[0])
        audios = [url for _, url in results]
        
        return audios
