from typing import Dict, List, Optional
import asyncio
import logging
import uuid
import os
import shutil
from pathlib import Path
from pydantic import BaseModel, Field

from .config import VideoComposerConfig
from ..base import create_storage, StorageBackend, TaskStorageManager
from ..base.exceptions import ValidationError, CompositionError

logger = logging.getLogger(__name__)


class VideoSegment(BaseModel):
    """视频片段信息"""
    path: str = Field(..., description="视频文件本地路径")
    duration: float = Field(..., description="视频时长(秒)", gt=0)
    width: Optional[int] = Field(None, description="视频宽度", gt=0)
    height: Optional[int] = Field(None, description="视频高度", gt=0)
    format: Optional[str] = Field(None, description="视频格式,如 mp4, avi 等")
    

class AudioSegment(BaseModel):
    """音频片段信息"""
    path: str = Field(..., description="音频文件本地路径")
    duration: float = Field(..., description="音频时长(秒)", gt=0)
    format: Optional[str] = Field(None, description="音频格式,如 mp3, wav 等")
    bitrate: Optional[str] = Field(None, description="音频比特率")


class VideoComposerAgent:
    
    def __init__(
        self,
        task_id: str,
        config: Optional[VideoComposerConfig] = None,
        storage: Optional[StorageBackend] = None,
    ):
        self.config = config or VideoComposerConfig()
        self.task_id = task_id
        self.logger = logging.getLogger(self.__class__.__name__)
        
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
    
    async def compose_video(
        self,
        video_segments: List[VideoSegment],
        audio_segments: List[AudioSegment],
        output_path: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        合成视频的主要方法
        
        Args:
            video_segments: 视频片段列表,每个片段必须包含路径、时长等基本信息
            audio_segments: 音频片段列表,每个片段必须包含路径、时长等基本信息
            output_path: 输出视频路径(可选),如果不提供则自动生成
        
        Returns:
            Dict[str, any]: 包含输出视频信息的字典
                - output_path: 输出视频的本地路径
                - duration: 视频总时长
                - file_size: 文件大小(字节)
        
        Raises:
            ValidationError: 输入参数验证失败
            CompositionError: 视频合成失败
        """
        self._validate_segments(video_segments, audio_segments)
        self._check_files_exist(video_segments, audio_segments)
        
        if len(video_segments) != len(audio_segments):
            raise ValidationError(
                f"视频片段数量({len(video_segments)})必须与音频片段数量({len(audio_segments)})相同"
            )
        
        try:
            clips = []
            for i, (video_seg, audio_seg) in enumerate(zip(video_segments, audio_segments)):
                clip_path = await self._merge_video_audio(
                    video_seg.path,
                    audio_seg.path,
                    i,
                )
                clips.append(clip_path)
            
            if output_path is None:
                output_path = str(self.temp_dir / f"final_{uuid.uuid4()}.mp4")
            
            final_video_path = await self._concatenate_clips(clips, output_path)
            
            file_size = os.path.getsize(final_video_path)
            duration = await self._get_video_duration(final_video_path)
            
            logger.info(f"成功合成视频: {final_video_path}")
            
            return {
                "output_path": final_video_path,
                "duration": duration,
                "file_size": file_size,
            }
        
        except Exception as e:
            logger.error(f"视频合成失败: {e}")
            raise CompositionError(f"视频合成失败: {e}") from e
    
    def _validate_segments(
        self,
        video_segments: List[VideoSegment],
        audio_segments: List[AudioSegment],
    ):
        """验证输入片段的有效性"""
        if not isinstance(video_segments, list):
            raise ValidationError("video_segments 必须是列表")
        
        if not isinstance(audio_segments, list):
            raise ValidationError("audio_segments 必须是列表")
        
        if len(video_segments) == 0:
            raise ValidationError("video_segments 不能为空")
        
        if len(audio_segments) == 0:
            raise ValidationError("audio_segments 不能为空")
        
        for i, seg in enumerate(video_segments):
            if not isinstance(seg, VideoSegment):
                raise ValidationError(f"video_segments[{i}] 必须是 VideoSegment 类型")
            if seg.duration <= 0:
                raise ValidationError(f"video_segments[{i}] 的时长必须大于0")
        
        for i, seg in enumerate(audio_segments):
            if not isinstance(seg, AudioSegment):
                raise ValidationError(f"audio_segments[{i}] 必须是 AudioSegment 类型")
            if seg.duration <= 0:
                raise ValidationError(f"audio_segments[{i}] 的时长必须大于0")
    
    def _check_files_exist(
        self,
        video_segments: List[VideoSegment],
        audio_segments: List[AudioSegment],
    ):
        """检查所有资源文件是否存在"""
        for i, seg in enumerate(video_segments):
            if not os.path.exists(seg.path):
                raise ValidationError(f"视频文件不存在: {seg.path} (video_segments[{i}])")
            if not os.path.isfile(seg.path):
                raise ValidationError(f"视频路径不是文件: {seg.path} (video_segments[{i}])")
        
        for i, seg in enumerate(audio_segments):
            if not os.path.exists(seg.path):
                raise ValidationError(f"音频文件不存在: {seg.path} (audio_segments[{i}])")
            if not os.path.isfile(seg.path):
                raise ValidationError(f"音频路径不是文件: {seg.path} (audio_segments[{i}])")
    
    async def health_check(self) -> bool:
        """健康检查:测试FFmpeg和存储"""
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
            if result.returncode != 0:
                raise Exception("FFmpeg not available")
            
            result = subprocess.run(['ffprobe', '-version'], capture_output=True)
            if result.returncode != 0:
                raise Exception("FFprobe not available")
            
            self.logger.info("VideoComposerAgent health check: OK")
            return True
        except Exception as e:
            self.logger.error(f"VideoComposerAgent health check failed: {e}")
            return False
    
    async def _merge_video_audio(
        self,
        video_path: str,
        audio_path: str,
        index: int,
    ) -> str:
        """合并单个视频和音频片段"""
        try:
            output_path = self.temp_dir / f"clip_{index}.mp4"
            cmd = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", self.config.audio_codec,
                "-b:a", self.config.audio_bitrate,
                "-shortest",
                str(output_path),
            ]
            
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
                raise CompositionError(f"合并视频音频失败 (片段 {index}): {error_msg}")
            
            logger.info(f"已合并视频音频片段 {index}: {output_path}")
            return str(output_path)
        
        except asyncio.TimeoutError:
            raise CompositionError(f"合并视频音频超时 (片段 {index})")
        except Exception as e:
            logger.error(f"合并视频音频失败 {index}: {e}")
            raise CompositionError(f"合并视频音频失败: {e}") from e
    
    async def _concatenate_clips(self, clip_paths: List[str], output_path: str) -> str:
        """拼接多个视频片段"""
        try:
            concat_file = self.temp_dir / "concat_list.txt"
            with open(concat_file, "w") as f:
                for clip_path in clip_paths:
                    abs_clip_path = os.path.abspath(clip_path)
                    f.write(f"file '{abs_clip_path}'\n")
            
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                output_path
            ]
            
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
                raise CompositionError(f"视频拼接失败: {error_msg}")
            
            concat_file.unlink()
            
            logger.info(f"已拼接视频: {output_path}")
            return output_path
        
        except asyncio.TimeoutError:
            raise CompositionError("视频拼接超时")
        except Exception as e:
            logger.error(f"视频拼接失败: {e}")
            raise CompositionError(f"视频拼接失败: {e}") from e
    
    async def _get_video_duration(self, video_path: str) -> float:
        """获取视频时长"""
        try:
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
                logger.warning("获取视频时长失败,返回 0.0")
                return 0.0
            
            data = json.loads(stdout.decode())
            duration = float(data.get("format", {}).get("duration", 0.0))
            
            return duration
        
        except Exception as e:
            logger.warning(f"获取视频时长失败: {e}")
            return 0.0
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"已清理临时目录: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
