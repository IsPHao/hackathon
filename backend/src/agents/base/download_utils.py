import aiohttp
from pathlib import Path
from typing import Optional
import logging

from .exceptions import DownloadError

logger = logging.getLogger(__name__)


async def download_to_bytes(url: str, timeout: int = 60, max_size: int = 50 * 1024 * 1024) -> bytes:
    if Path(url).exists():
        file_path = Path(url)
        file_size = file_path.stat().st_size
        if file_size > max_size:
            raise DownloadError(f"File too large: {file_size} bytes (max: {max_size})")
        return file_path.read_bytes()
    
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    try:
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise DownloadError(f"Download failed: HTTP {response.status}")
                
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > max_size:
                    raise DownloadError(
                        f"File too large: {content_length} bytes (max: {max_size})"
                    )
                
                data = bytearray()
                async for chunk in response.content.iter_chunked(8192):
                    data.extend(chunk)
                    if len(data) > max_size:
                        raise DownloadError(
                            f"Downloaded data exceeded max size: {max_size} bytes"
                        )
                
                logger.debug(f"Downloaded {len(data)} bytes from {url}")
                return bytes(data)
    
    except aiohttp.ClientError as e:
        logger.error(f"Failed to download from {url}: {e}")
        raise DownloadError(f"Failed to download file: {e}") from e
    
    except Exception as e:
        logger.error(f"Unexpected error downloading from {url}: {e}")
        raise DownloadError(f"Failed to download file: {e}") from e


async def download_file(url: str, destination: str, timeout: int = 60, max_size: int = 50 * 1024 * 1024) -> str:
    try:
        data = await download_to_bytes(url, timeout, max_size)
        
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        
        logger.info(f"Downloaded file saved to: {destination}")
        return destination
    
    except Exception as e:
        logger.error(f"Failed to download and save file: {e}")
        raise DownloadError(f"Failed to download and save file: {e}") from e
