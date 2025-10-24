import aiohttp
from pathlib import Path
from typing import Optional
import logging

from .exceptions import DownloadError

logger = logging.getLogger(__name__)


async def download_to_bytes(url: str, timeout: int = 60) -> bytes:
    if Path(url).exists():
        return Path(url).read_bytes()
    
    try:
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise DownloadError(f"Download failed: HTTP {response.status}")
                
                data = await response.read()
                logger.debug(f"Downloaded {len(data)} bytes from {url}")
                return data
    
    except aiohttp.ClientError as e:
        logger.error(f"Failed to download from {url}: {e}")
        raise DownloadError(f"Failed to download file: {e}") from e
    
    except Exception as e:
        logger.error(f"Unexpected error downloading from {url}: {e}")
        raise DownloadError(f"Failed to download file: {e}") from e


async def download_file(url: str, destination: str, timeout: int = 60) -> str:
    try:
        data = await download_to_bytes(url, timeout)
        
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        
        logger.info(f"Downloaded file saved to: {destination}")
        return destination
    
    except Exception as e:
        logger.error(f"Failed to download and save file: {e}")
        raise DownloadError(f"Failed to download and save file: {e}") from e
