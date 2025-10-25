from typing import Dict, List, Optional, Any
import asyncio
import logging
import uuid
import os
import aiohttp
import shutil
from pathlib import Path

from .config import VideoComposerConfig
from ..base import create_storage, StorageBackend, TaskStorageManager
from ..base.agent import BaseAgent
from ..base.exceptions import ValidationError, CompositionError, DownloadError

logger = logging.getLogger(__name__)


class VideoComposerAgent(BaseAgent[VideoComposerConfig]):
    
    def __init__(
        self,
        task_id: str,
        config: Optional[VideoComposerConfig] = None,
        storage: Optional[StorageBackend] = None,
    ):
        super().__init__(config)
        self.task_id = task_id
        
        self.task_storage = TaskStorageManager(
            task_id,
            base_path=self.config.task_storage_base_path
        )
        
        if storage:
            self.storage = storage
        else:
            self.storage = create_storage(
                storage_type=self.config.storage_type,
                base_path=self.config.local_storage_path,
                bucket=self.config.oss_bucket,
                endpoint=self.config.oss_endpoint,
                access_key=self.config.oss_access_key,
                secret_key=self.config.oss_secret_key,
            )
        
        self.temp_dir = self.task_storage.temp_dir
    
    def _default_config(self) -> VideoComposerConfig:
        return VideoComposerConfig()
    
    async def execute(self, images: List[str], audios: List[str], storyboard: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        执行视频合成(统一接口)
        
        Args:
            images: 图像列表
            audios: 音频列表
            storyboard: 分镜数据
            **kwargs: 其他参数
        
        Returns:
            Dict[str, Any]: 视频信息
        """
        return await self.compose(images, audios, storyboard)
    
    async def health_check(self) -> bool:
        """健康检查:测试FFmpeg和存储"""
        try:
            # 测试FFmpeg
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
            if result.returncode != 0:
                raise Exception("FFmpeg not available")
            # 测试存储
            if hasattr(self.storage, 'health_check'):
                storage_ok = await self.storage.health_check()
                if not storage_ok:
                    raise Exception("Storage health check failed")
            self.logger.info("VideoComposerAgent health check: OK")
            return True
        except Exception as e:
            self.logger.error(f"VideoComposerAgent health check failed: {e}")
            return False
    
    async def compose(
        self,
        images: List[str],
        audios: List[str],
        storyboard: Dict[str, Any],
    ) -> Dict[str, Any]:
        self._validate_inputs(images, audios, storyboard)
        
        scenes = storyboard.get("scenes", [])
        if len(images) != len(scenes):
            raise ValidationError(f"Number of images ({len(images)}) must match scenes ({len(scenes)})")
        
        if len(audios) != len(scenes):
            raise ValidationError(f"Number of audios ({len(audios)}) must match scenes ({len(scenes)})")
        
        try:
            local_images = await self._download_resources(images, "images")
            local_audios = await self._download_resources(audios, "audios")
            
            clips = []
            for i, scene in enumerate(scenes):
                clip_path = await self._create_scene_clip(
                    local_images[i],
                    local_audios[i],
                    scene,
                    i,
                )
                clips.append(clip_path)
            
            output_path = await self._concatenate_clips(clips)
            
            video_url = await self._upload_video(output_path)
            thumbnail_url = await self._generate_thumbnail(output_path)
            
            file_size = os.path.getsize(output_path)
            duration = await self._get_video_duration(output_path)
            
            # self._cleanup_temp_files([output_path] + clips + local_images + local_audios)
            
            logger.info(f"Successfully composed video: {video_url}")
            
            return {
                "url": video_url,
                "thumbnail_url": thumbnail_url,
                "duration": duration,
                "file_size": file_size,
            }
        
        except Exception as e:
            logger.error(f"Failed to compose video: {e}")
            raise CompositionError(f"Video composition failed: {e}") from e
    
    async def _create_scene_clip(
        self,
        image_path: str,
        audio_path: str,
        scene: Dict[str, Any],
        index: int,
    ) -> str:
        try:
            import subprocess
            
            output_path = self.temp_dir / f"clip_{index}.mp4"
            cmd = self._build_scene_ffmpeg_cmd(image_path, audio_path, output_path, scene)
            
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
                raise CompositionError(f"FFmpeg failed for scene {index}: {error_msg}")
            
            logger.info(f"Created scene clip {index}: {output_path}")
            return str(output_path)
        
        except asyncio.TimeoutError:
            raise CompositionError(f"Scene clip creation timed out for scene {index}")
        except ImportError:
            raise CompositionError("FFmpeg is not available. Please install ffmpeg.")
        except Exception as e:
            logger.error(f"Failed to create scene clip {index}: {e}")
            raise CompositionError(f"Failed to create scene clip: {e}") from e
    
    def _build_scene_ffmpeg_cmd(
        self,
        image_path: str,
        audio_path: str,
        output_path: str,
        scene: Dict[str, Any]
    ) -> List[str]:
        """
        Build FFmpeg command for creating a scene clip.
        
        Args:
            image_path: Path to the image file
            audio_path: Path to the audio file
            output_path: Path for the output video clip
            scene: Scene data containing duration
            
        Returns:
            List[str]: FFmpeg command as list of arguments
        """
        duration = scene.get("duration", 3.0)
        
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
    
    def _build_concat_ffmpeg_cmd(
        self,
        concat_list_path: str,
        output_path: str
    ) -> List[str]:
        """
        Build FFmpeg command for concatenating video clips.
        
        Args:
            concat_list_path: Path to the concat list file
            output_path: Path for the final output video
            
        Returns:
            List[str]: FFmpeg command as list of arguments
        """
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
    
    async def _concatenate_clips(self, clip_paths: List[str]) -> str:
        try:
            import subprocess
            
            concat_file = self.temp_dir / "concat_list.txt"
            with open(concat_file, "w") as f:
                for clip_path in clip_paths:
                    # Use absolute paths in the concat list file
                    abs_clip_path = os.path.abspath(clip_path)
                    f.write(f"file '{abs_clip_path}'\n")
            
            output_path = self.temp_dir / f"final_{uuid.uuid4()}.mp4"
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
            
            logger.info(f"Concatenated clips into: {output_path}")
            return str(output_path)
        
        except asyncio.TimeoutError:
            raise CompositionError("Video concatenation timed out")
        except Exception as e:
            logger.error(f"Failed to concatenate clips: {e}")
            raise CompositionError(f"Failed to concatenate clips: {e}") from e
    
    async def _download_resources(
        self,
        urls: List[str],
        resource_type: str,
    ) -> List[str]:
        tasks = [
            self._download_resource(url, resource_type, i)
            for i, url in enumerate(urls)
        ]
        return await asyncio.gather(*tasks)
    
    async def _download_resource(
        self,
        url: str,
        resource_type: str,
        index: int,
    ) -> str:
        # If it's a local file path, copy it to our temp directory
        if os.path.exists(url):
            logger.info(f"Using local resource: {url}")
            ext = Path(url).suffix or (".png" if resource_type == "images" else ".mp3")
            local_path = self.temp_dir / f"{resource_type}_{index}{ext}"
            
            # Copy the file to our temp directory
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: shutil.copy2(url, local_path)
            )
            
            logger.info(f"Copied local {resource_type} {index}: {local_path}")
            return str(local_path)
        
        # If it's a URL, download it
        try:
            ext = Path(url).suffix or (".png" if resource_type == "images" else ".mp3")
            local_path = self.temp_dir / f"{resource_type}_{index}{ext}"
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise DownloadError(f"Failed to download {resource_type}: HTTP {response.status}")
                    
                    data = await response.read()
                    
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: local_path.write_bytes(data)
                    )
            
            logger.info(f"Downloaded {resource_type} {index}: {local_path}")
            return str(local_path)
        
        except Exception as e:
            logger.error(f"Failed to download {resource_type} {index}: {e}")
            raise DownloadError(f"Failed to download {resource_type}: {e}") from e
    
    async def _upload_video(self, video_path: str) -> str:
        try:
            filename = f"video_{uuid.uuid4()}.mp4"
            url = await self.storage.save_file(video_path, filename)
            logger.info(f"Uploaded video: {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to upload video: {e}")
            raise CompositionError(f"Failed to upload video: {e}") from e
    
    async def _generate_thumbnail(self, video_path: str) -> str:
        try:
            import subprocess
            
            thumbnail_path = self.temp_dir / f"thumbnail_{uuid.uuid4()}.jpg"
            
            cmd = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-vframes", "1",
                "-ss", "00:00:01",
                "-vf", "scale=320:-1",
                str(thumbnail_path),
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            await process.communicate()
            
            if process.returncode != 0:
                logger.warning("Failed to generate thumbnail, using empty string")
                return ""
            
            filename = f"thumbnail_{uuid.uuid4()}.jpg"
            url = await self.storage.save_file(str(thumbnail_path), filename)
            
            thumbnail_path.unlink()
            
            logger.info(f"Generated thumbnail: {url}")
            return url
        
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail: {e}")
            return ""
    
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
    
    def _cleanup_temp_files(self, file_paths: List[str]):
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
    
    def _validate_inputs(
        self,
        images: List[str],
        audios: List[str],
        storyboard: Dict[str, Any],
    ):
        if not isinstance(images, list):
            raise ValidationError("Images must be a list")
        
        if not isinstance(audios, list):
            raise ValidationError("Audios must be a list")
        
        if not isinstance(storyboard, dict):
            raise ValidationError("Storyboard must be a dictionary")
        
        if "scenes" not in storyboard:
            raise ValidationError("Storyboard must have 'scenes' key")
        
        if not isinstance(storyboard["scenes"], list):
            raise ValidationError("Storyboard 'scenes' must be a list")
        
        if len(images) == 0:
            raise ValidationError("Images list cannot be empty")
        
        if len(audios) == 0:
            raise ValidationError("Audios list cannot be empty")
