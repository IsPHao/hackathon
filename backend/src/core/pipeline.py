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
        config: Optional[CoreSettings] = None
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
    
    async def execute(
        self,
        project_id: UUID,
        novel_text: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
    ):
        max_retries = max_retries or self.config.max_retries
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
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
        scenes = storyboard_data.get("scenes", [])
        total_scenes = len(scenes)
        images = []
        
        for i, scene in enumerate(scenes):
            image_url = await self._execute_with_retry(
                self.image_generator.generate,
                scene,
                character_data,
                str(project_id)
            )
            images.append(image_url)
            
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
        storyboard_data: Dict[str, Any]
    ) -> List[str]:
        scenes = storyboard_data.get("scenes", [])
        total_scenes = len(scenes)
        audios = []
        
        for i, scene in enumerate(scenes):
            audio_url = await self._execute_with_retry(
                self.voice_synthesizer.synthesize,
                scene,
                str(project_id)
            )
            audios.append(audio_url)
            
            progress = 70 + int((i + 1) / total_scenes * 10)
            await self.progress_tracker.update(
                project_id,
                "content_generation",
                progress,
                f"已生成 {i + 1}/{total_scenes} 个场景音频"
            )
        
        return audios
