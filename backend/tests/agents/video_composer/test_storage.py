import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

from src.agents.base import (
    LocalStorage,
    OSSStorage,
    create_storage,
    StorageError,
)


@pytest.fixture
def temp_dir():
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_local_storage_save(temp_dir):
    storage = LocalStorage(base_path=temp_dir)
    
    video_data = b"fake video data"
    filename = "test_video.mp4"
    
    result = await storage.save(video_data, filename)
    
    assert str(Path(temp_dir) / filename) == result
    assert Path(result).exists()
    assert Path(result).read_bytes() == video_data


@pytest.mark.asyncio
async def test_local_storage_save_file(temp_dir):
    storage = LocalStorage(base_path=temp_dir)
    
    source_file = Path(temp_dir) / "source.mp4"
    source_file.write_bytes(b"fake video data")
    
    filename = "test_video.mp4"
    
    result = await storage.save_file(str(source_file), filename)
    
    assert str(Path(temp_dir) / filename) == result
    assert Path(result).exists()
    assert Path(result).read_bytes() == b"fake video data"


@pytest.mark.asyncio
async def test_local_storage_save_error(temp_dir):
    storage = LocalStorage(base_path=temp_dir)
    
    with patch("pathlib.Path.write_bytes", side_effect=Exception("Write error")):
        with pytest.raises(StorageError, match="Failed to save file"):
            await storage.save(b"data", "test.mp4")


@pytest.mark.asyncio
async def test_oss_storage_save():
    with pytest.MonkeyPatch().context() as mp:
        # Mock the oss2 module
        mock_oss2 = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.put_object = MagicMock(return_value=MagicMock())
        mock_oss2.Bucket = MagicMock(return_value=mock_bucket)
        mp.setitem(sys.modules, 'oss2', mock_oss2)
        
        storage = OSSStorage(
            bucket="test-bucket",
            endpoint="oss-cn-hangzhou.aliyuncs.com",
            access_key="test-key",
            secret_key="test-secret",
        )
    
        result = await storage.save(b"video data", "test.mp4")
        
        assert "test-bucket" in result
        assert "test.mp4" in result
        assert mock_bucket.put_object.called


@pytest.mark.asyncio
async def test_oss_storage_save_file(temp_dir):
    with pytest.MonkeyPatch().context() as mp:
        # Mock the oss2 module
        mock_oss2 = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.put_object = MagicMock(return_value=MagicMock())
        mock_oss2.Bucket = MagicMock(return_value=mock_bucket)
        mp.setitem(sys.modules, 'oss2', mock_oss2)
        
        storage = OSSStorage(
            bucket="test-bucket",
            endpoint="oss-cn-hangzhou.aliyuncs.com",
            access_key="test-key",
            secret_key="test-secret",
        )
        
        source_file = Path(temp_dir) / "source.mp4"
        source_file.write_bytes(b"fake video data")
        
        result = await storage.save_file(str(source_file), "test.mp4")
        
        assert "test-bucket" in result
        assert "test.mp4" in result
        assert mock_bucket.put_object.called


@pytest.mark.asyncio
async def test_oss_storage_missing_oss2():
    storage = OSSStorage(
        bucket="test-bucket",
        endpoint="oss-cn-hangzhou.aliyuncs.com",
        access_key="test-key",
        secret_key="test-secret",
    )
    
    with patch.dict("sys.modules", {"oss2": None}):
        with pytest.raises(StorageError, match="oss2 package is required"):
            await storage.save(b"data", "test.mp4")


def test_create_storage_local(temp_dir):
    storage = create_storage("local", base_path=temp_dir)
    
    assert isinstance(storage, LocalStorage)
    assert str(storage.base_path) == temp_dir


def test_create_storage_oss():
    storage = create_storage(
        "oss",
        bucket="test-bucket",
        endpoint="oss-cn-hangzhou.aliyuncs.com",
        access_key="test-key",
        secret_key="test-secret",
    )
    
    assert isinstance(storage, OSSStorage)
    assert storage.bucket == "test-bucket"


def test_create_storage_invalid_type():
    with pytest.raises(ValueError, match="Unknown storage type"):
        create_storage("invalid")
