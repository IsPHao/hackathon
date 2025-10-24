import os
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import logging

from .exceptions import StorageError

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    
    @abstractmethod
    async def save(self, video_data: bytes, filename: str) -> str:
        pass
    
    @abstractmethod
    async def save_file(self, file_path: str, filename: str) -> str:
        pass


class LocalStorage(StorageBackend):
    
    def __init__(self, base_path: str = "./data/videos"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def save(self, video_data: bytes, filename: str) -> str:
        try:
            file_path = self.base_path / filename
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: file_path.write_bytes(video_data)
            )
            
            logger.info(f"Video saved to local storage: {file_path}")
            return str(file_path)
        
        except Exception as e:
            logger.error(f"Failed to save video to local storage: {e}")
            raise StorageError(f"Failed to save video: {e}") from e
    
    async def save_file(self, file_path: str, filename: str) -> str:
        try:
            dest_path = self.base_path / filename
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: dest_path.write_bytes(Path(file_path).read_bytes())
            )
            
            logger.info(f"Video file saved to local storage: {dest_path}")
            return str(dest_path)
        
        except Exception as e:
            logger.error(f"Failed to save video file to local storage: {e}")
            raise StorageError(f"Failed to save video file: {e}") from e


class OSSStorage(StorageBackend):
    
    def __init__(
        self,
        bucket: str,
        endpoint: str,
        access_key: str,
        secret_key: str,
    ):
        self.bucket = bucket
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
    
    async def save(self, video_data: bytes, filename: str) -> str:
        try:
            import oss2
            
            auth = oss2.Auth(self.access_key, self.secret_key)
            bucket = oss2.Bucket(auth, self.endpoint, self.bucket)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: bucket.put_object(filename, video_data)
            )
            
            url = f"https://{self.bucket}.{self.endpoint}/{filename}"
            logger.info(f"Video uploaded to OSS: {url}")
            return url
        
        except ImportError:
            raise StorageError("oss2 package is required for OSS storage. Install it with: pip install oss2")
        
        except Exception as e:
            logger.error(f"Failed to upload video to OSS: {e}")
            raise StorageError(f"Failed to upload video: {e}") from e
    
    async def save_file(self, file_path: str, filename: str) -> str:
        try:
            import oss2
            
            auth = oss2.Auth(self.access_key, self.secret_key)
            bucket = oss2.Bucket(auth, self.endpoint, self.bucket)
            
            loop = asyncio.get_event_loop()
            with open(file_path, 'rb') as f:
                result = await loop.run_in_executor(
                    None,
                    lambda: bucket.put_object(filename, f)
                )
            
            url = f"https://{self.bucket}.{self.endpoint}/{filename}"
            logger.info(f"Video file uploaded to OSS: {url}")
            return url
        
        except ImportError:
            raise StorageError("oss2 package is required for OSS storage. Install it with: pip install oss2")
        
        except Exception as e:
            logger.error(f"Failed to upload video file to OSS: {e}")
            raise StorageError(f"Failed to upload video file: {e}") from e


def create_storage(storage_type: str, **kwargs) -> StorageBackend:
    if storage_type == "local":
        return LocalStorage(kwargs.get("base_path", "./data/videos"))
    elif storage_type == "oss":
        return OSSStorage(
            bucket=kwargs.get("bucket", ""),
            endpoint=kwargs.get("endpoint", ""),
            access_key=kwargs.get("access_key", ""),
            secret_key=kwargs.get("secret_key", ""),
        )
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
