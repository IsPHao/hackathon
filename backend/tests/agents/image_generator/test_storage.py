import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.image_generator import (
    LocalStorage,
    OSSStorage,
    create_storage,
    StorageError,
)


@pytest.fixture
def temp_dir():
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_image_data():
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 1000


@pytest.mark.asyncio
async def test_local_storage_save(temp_dir, sample_image_data):
    storage = LocalStorage(base_path=temp_dir)
    
    filename = "test_image.png"
    result = await storage.save(sample_image_data, filename)
    
    assert result == str(Path(temp_dir) / filename)
    assert Path(result).exists()
    assert Path(result).read_bytes() == sample_image_data


@pytest.mark.asyncio
async def test_local_storage_create_directory(temp_dir, sample_image_data):
    new_path = Path(temp_dir) / "new_subdir"
    storage = LocalStorage(base_path=str(new_path))
    
    filename = "test_image.png"
    result = await storage.save(sample_image_data, filename)
    
    assert new_path.exists()
    assert Path(result).exists()


@pytest.mark.asyncio
async def test_local_storage_save_error(temp_dir):
    storage = LocalStorage(base_path=temp_dir)
    
    with pytest.raises(StorageError):
        await storage.save(b"data", "/invalid/path/../../../test.png")


@pytest.mark.asyncio
async def test_oss_storage_save():
    storage = OSSStorage(
        bucket="test-bucket",
        endpoint="oss-cn-hangzhou.aliyuncs.com",
        access_key="test-key",
        secret_key="test-secret",
    )
    
    sample_data = b"test data"
    
    mock_oss2 = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.put_object.return_value = MagicMock()
    mock_oss2.Auth.return_value = MagicMock()
    mock_oss2.Bucket.return_value = mock_bucket
    
    with patch.dict('sys.modules', {'oss2': mock_oss2}):
        result = await storage.save(sample_data, "test.png")
        
        assert "test-bucket" in result
        assert "test.png" in result
        mock_bucket.put_object.assert_called_once_with("test.png", sample_data)


@pytest.mark.asyncio
async def test_oss_storage_missing_package():
    storage = OSSStorage(
        bucket="test-bucket",
        endpoint="endpoint",
        access_key="key",
        secret_key="secret",
    )
    
    import sys
    original_modules = sys.modules.copy()
    if 'oss2' in sys.modules:
        del sys.modules['oss2']
    
    with patch.dict('sys.modules', {'oss2': None}):
        with pytest.raises(StorageError, match="oss2 package is required"):
            await storage.save(b"data", "test.png")
    
    sys.modules.update(original_modules)


def test_create_storage_local(temp_dir):
    storage = create_storage("local", base_path=temp_dir)
    
    assert isinstance(storage, LocalStorage)
    assert storage.base_path == Path(temp_dir)


def test_create_storage_oss():
    storage = create_storage(
        "oss",
        bucket="bucket",
        endpoint="endpoint",
        access_key="key",
        secret_key="secret",
    )
    
    assert isinstance(storage, OSSStorage)
    assert storage.bucket == "bucket"


def test_create_storage_invalid_type():
    with pytest.raises(ValueError, match="Unknown storage type"):
        create_storage("invalid-type")
