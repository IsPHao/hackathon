from typing import Dict, List, Optional, Any
import asyncio
import logging
import uuid
import os
from pathlib import Path

from .config import SceneComposerConfig
from ..base import TaskStorageManager
from ..base.agent import BaseAgent
from ..base.exceptions import ValidationError, CompositionError
from ..scene_renderer.models import RenderResult, RenderedChapter, RenderedScene

logger = logging.getLogger(__name__)


class SceneComposer(BaseAgent[SceneComposerConfig]):
    
    def __init__(
        self,
        task_id: str,
        config: Optional[SceneComposerConfig] = None,
    ):
        super().__init__(config)
        self.task_id = task_id
        
        self.task_storage = TaskStorageManager(
            task_id,
            base_path=self.config.task_storage_base_path
        )
        
        self.temp_dir = self.task_storage.temp_dir
    
    def _default_config(self) -> SceneComposerConfig:
        return SceneComposerConfig()
    
    async def execute(self, render_result: RenderResult, **kwargs) -> Dict[str, Any]:
        return await self.compose(render_result)
    
    async def health_check(self) -> bool:
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
            if result.returncode != 0:
                raise Exception("FFmpeg not available")
            self.logger.info("SceneComposer health check: OK")
            return True
        except Exception as e:
            self.logger.error(f"SceneComposer health check failed: {e}")
            return False
    
    async def compose(self, render_result: RenderResult) -> Dict[str, Any]:
        self._validate_input(render_result)
        
        try:
            chapter_videos = []
            for chapter in render_result.chapters:
                chapter_video_path = await self._compose_chapter(chapter)
                chapter_videos.append(chapter_video_path)
            
            if len(chapter_videos) == 1:
                final_video_path = chapter_videos[0]
            else:
                final_video_path = await self._concatenate_videos(
                    chapter_videos,
                    "final_video"
                )
            
            file_size = os.path.getsize(final_video_path)
            duration = await self._get_video_duration(final_video_path)
            
            logger.info(f"Successfully composed final video: {final_video_path}")
            
            return {
                "video_path": final_video_path,
                "duration": duration,
                "file_size": file_size,
                "total_scenes": render_result.total_scenes,
                "total_chapters": len(render_result.chapters),
            }
        
        except Exception as e:
            logger.error(f"Failed to compose video: {e}")
            raise CompositionError(f"Video composition failed: {e}") from e
    
    async def _compose_chapter(self, chapter: RenderedChapter) -> str:
        scene_videos = []
        for scene in chapter.scenes:
            scene_video_path = await self._compose_scene(scene)
            scene_videos.append(scene_video_path)
        
        if len(scene_videos) == 1:
            return scene_videos[0]
        
        chapter_video_path = await self._concatenate_videos(
            scene_videos,
            f"chapter_{chapter.chapter_id}"
        )
        
        logger.info(f"Composed chapter {chapter.chapter_id}: {chapter_video_path}")
        return chapter_video_path
    
    async def _compose_scene(self, scene: RenderedScene) -> str:
        try:
            import subprocess
            
            output_path = self.temp_dir / f"scene_{scene.scene_id}_{uuid.uuid4().hex[:8]}.mp4"
            
            if not os.path.exists(scene.image_path):
                raise CompositionError(f"Image file not found: {scene.image_path}")
            if not os.path.exists(scene.audio_path):
                raise CompositionError(f"Audio file not found: {scene.audio_path}")
            
            duration = max(scene.duration, scene.audio_duration)
            
            cmd = self._build_scene_ffmpeg_cmd(
                scene.image_path,
                scene.audio_path,
                str(output_path),
                duration
            )
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout,
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise CompositionError(f"FFmpeg failed for scene {scene.scene_id}: {error_msg}")
            
            logger.info(f"Composed scene {scene.scene_id}: {output_path}")
            return str(output_path)
        
        except asyncio.TimeoutError:
            raise CompositionError(f"Scene composition timed out for scene {scene.scene_id}")
        except ImportError:
            raise CompositionError("FFmpeg is not available. Please install ffmpeg.")
        except Exception as e:
            logger.error(f"Failed to compose scene {scene.scene_id}: {e}")
            raise CompositionError(f"Failed to compose scene: {e}") from e
    
    def _build_scene_ffmpeg_cmd(
        self,
        image_path: str,
        audio_path: str,
        output_path: str,
        duration: float
    ) -> List[str]:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-c:v", self.config.codec,
            "-preset", self.config.preset,
            "-tune", "stillimage",
            "-c:a", self.config.audio_codec,
            "-b:a", self.config.audio_bitrate,
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-t", str(duration),
            output_path,
        ]
        
        return cmd
    
    async def _concatenate_videos(
        self,
        video_paths: List[str],
        output_name: str
    ) -> str:
        try:
            import subprocess
            
            concat_file = self.temp_dir / f"{output_name}_concat_{uuid.uuid4().hex[:8]}.txt"
            with open(concat_file, "w") as f:
                for video_path in video_paths:
                    abs_video_path = os.path.abspath(video_path)
                    f.write(f"file '{abs_video_path}'\n")
            
            output_path = self.temp_dir / f"{output_name}_{uuid.uuid4().hex[:8]}.mp4"
            cmd = self._build_concat_ffmpeg_cmd(str(concat_file), str(output_path))
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout,
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise CompositionError(f"FFmpeg concatenation failed: {error_msg}")
            
            concat_file.unlink()
            
            logger.info(f"Concatenated videos into: {output_path}")
            return str(output_path)
        
        except asyncio.TimeoutError:
            raise CompositionError("Video concatenation timed out")
        except Exception as e:
            logger.error(f"Failed to concatenate videos: {e}")
            raise CompositionError(f"Failed to concatenate videos: {e}") from e
    
    def _build_concat_ffmpeg_cmd(
        self,
        concat_list_path: str,
        output_path: str
    ) -> List[str]:
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            output_path
        ]
        
        return cmd
    
    async def _get_video_duration(self, video_path: str) -> float:
        try:
            import subprocess
            import json
            
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                video_path,
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.warning("Failed to get video duration, using 0.0")
                return 0.0
            
            data = json.loads(stdout.decode())
            duration = float(data.get("format", {}).get("duration", 0.0))
            
            return duration
        
        except Exception as e:
            logger.warning(f"Failed to get video duration: {e}")
            return 0.0
    
    def _validate_input(self, render_result: RenderResult):
        if not isinstance(render_result, RenderResult):
            raise ValidationError("Input must be a RenderResult instance")
        
        if not render_result.chapters:
            raise ValidationError("RenderResult must have at least one chapter")
        
        for chapter in render_result.chapters:
            if not chapter.scenes:
                raise ValidationError(f"Chapter {chapter.chapter_id} must have at least one scene")
            
            for scene in chapter.scenes:
                if not scene.image_path:
                    raise ValidationError(f"Scene {scene.scene_id} must have an image_path")
                if not scene.audio_path:
                    raise ValidationError(f"Scene {scene.scene_id} must have an audio_path")
