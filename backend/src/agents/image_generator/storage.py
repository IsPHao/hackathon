import os
import asyncio
import aiohttp
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import logging

from .exceptions import StorageError

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    
    @abstractmethod
    async def save(self, image_data: bytes, filename: str) -> str:
        pass


class LocalStorage(StorageBackend):
    
    def __init__(self, base_path: str = "./data/images"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def save(self, image_data: bytes, filename: str) -> str:
        try:
            file_path = self.base_path / filename
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: file_path.write_bytes(image_data)
            )
            
            logger.info(f"Image saved to local storage: {file_path}")
            return str(file_path)
        
        except Exception as e:
            logger.error(f"Failed to save image to local storage: {e}")
            raise StorageError(f"Failed to save image: {e}") from e


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
    
    async def save(self, image_data: bytes, filename: str) -> str:
        try:
            import oss2
            
            auth = oss2.Auth(self.access_key, self.secret_key)
            bucket = oss2.Bucket(auth, self.endpoint, self.bucket)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: bucket.put_object(filename, image_data)
            )
            
            url = f"https://{self.bucket}.{self.endpoint}/{filename}"
            logger.info(f"Image uploaded to OSS: {url}")
            return url
        
        except ImportError:
            raise StorageError("oss2 package is required for OSS storage. Install it with: pip install oss2")
        
        except Exception as e:
            logger.error(f"Failed to upload image to OSS: {e}")
            raise StorageError(f"Failed to upload image: {e}") from e


def create_storage(storage_type: str, **kwargs) -> StorageBackend:
    if storage_type == "local":
        return LocalStorage(kwargs.get("base_path", "./data/images"))
    elif storage_type == "oss":
        return OSSStorage(
            bucket=kwargs.get("bucket", ""),
            endpoint=kwargs.get("endpoint", ""),
            access_key=kwargs.get("access_key", ""),
            secret_key=kwargs.get("secret_key", ""),
        )
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
