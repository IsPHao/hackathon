import os
import asyncio
from pathlib import Path
from typing import Optional
import logging

from .exceptions import StorageError

logger = logging.getLogger(__name__)


class TaskStorageManager:
    
    def __init__(self, task_id: str, base_path: str = "./generated_files"):
        self.task_id = task_id
        self.base_path = Path(base_path).resolve() / task_id
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.images_dir = self.base_path / "images"
        self.audio_dir = self.base_path / "audio"
        self.temp_dir = self.base_path / "temp"
        self.videos_dir = self.base_path / "videos"
        
        self.images_dir.mkdir(exist_ok=True)
        self.audio_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        self.videos_dir.mkdir(exist_ok=True)
    
    async def save_image(self, image_data: bytes, filename: str) -> str:
        try:
            file_path = self.images_dir / filename
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: file_path.write_bytes(image_data)
            )
            
            logger.info(f"Image saved to task storage: {file_path}")
            return str(file_path)
        
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            raise StorageError(f"Failed to save image: {e}") from e
    
    async def save_audio(self, audio_data: bytes, filename: str) -> str:
        try:
            file_path = self.audio_dir / filename
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: file_path.write_bytes(audio_data)
            )
            
            logger.info(f"Audio saved to task storage: {file_path}")
            return str(file_path)
        
        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            raise StorageError(f"Failed to save audio: {e}") from e
    
    async def save_temp(self, data: bytes, filename: str) -> str:
        try:
            file_path = self.temp_dir / filename
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: file_path.write_bytes(data)
            )
            
            logger.debug(f"Temp file saved: {file_path}")
            return str(file_path)
        
        except Exception as e:
            logger.error(f"Failed to save temp file: {e}")
            raise StorageError(f"Failed to save temp file: {e}") from e
    
    def get_image_path(self, filename: str) -> str:
        return str(self.images_dir / filename)
    
    def get_audio_path(self, filename: str) -> str:
        return str(self.audio_dir / filename)
    
    def get_temp_path(self, filename: str) -> str:
        return str(self.temp_dir / filename)
    
    def get_video_path(self, filename: str) -> str:
        return str(self.videos_dir / filename)
    
    async def cleanup_temp(self):
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._cleanup_directory,
                self.temp_dir
            )
            logger.info(f"Cleaned up temp directory for task {self.task_id}")
        
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")
    
    def _cleanup_directory(self, directory: Path):
        if directory.exists():
            for file_path in directory.iterdir():
                try:
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        import shutil
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")
