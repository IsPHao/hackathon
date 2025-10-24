import pytest
import tempfile
import shutil
from pathlib import Path

from src.agents.character_consistency import LocalFileStorage, StorageError


@pytest.fixture
def temp_storage_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage(temp_storage_dir):
    return LocalFileStorage(base_path=temp_storage_dir)


@pytest.fixture
def sample_character_data():
    return {
        "base_prompt": "anime style, young male student",
        "negative_prompt": "low quality, blurry",
        "features": {
            "gender": "male",
            "age": 16,
            "hair": "short black hair",
            "eyes": "brown eyes",
        },
    }


@pytest.mark.asyncio
async def test_save_character(storage, sample_character_data):
    project_id = "test_project"
    character_name = "测试角色"
    
    file_path = await storage.save_character(project_id, character_name, sample_character_data)
    
    assert file_path is not None
    assert Path(file_path).exists()


@pytest.mark.asyncio
async def test_load_character(storage, sample_character_data):
    project_id = "test_project"
    character_name = "测试角色"
    
    await storage.save_character(project_id, character_name, sample_character_data)
    
    loaded_data = await storage.load_character(project_id, character_name)
    
    assert loaded_data is not None
    assert loaded_data["name"] == character_name
    assert loaded_data["base_prompt"] == sample_character_data["base_prompt"]


@pytest.mark.asyncio
async def test_load_nonexistent_character(storage):
    project_id = "test_project"
    character_name = "nonexistent"
    
    loaded_data = await storage.load_character(project_id, character_name)
    
    assert loaded_data is None


@pytest.mark.asyncio
async def test_character_exists(storage, sample_character_data):
    project_id = "test_project"
    character_name = "测试角色"
    
    exists_before = await storage.character_exists(project_id, character_name)
    assert exists_before is False
    
    await storage.save_character(project_id, character_name, sample_character_data)
    
    exists_after = await storage.character_exists(project_id, character_name)
    assert exists_after is True


@pytest.mark.asyncio
async def test_save_reference_image(storage, sample_character_data):
    project_id = "test_project"
    character_name = "测试角色"
    image_url = "https://example.com/image.png"
    
    await storage.save_character(project_id, character_name, sample_character_data)
    
    result_url = await storage.save_reference_image(project_id, character_name, image_url)
    
    assert result_url == image_url
    
    loaded_data = await storage.load_character(project_id, character_name)
    assert loaded_data["reference_image_url"] == image_url


@pytest.mark.asyncio
async def test_save_reference_image_nonexistent_character(storage):
    project_id = "test_project"
    character_name = "nonexistent"
    image_url = "https://example.com/image.png"
    
    with pytest.raises(StorageError, match="not found"):
        await storage.save_reference_image(project_id, character_name, image_url)


@pytest.mark.asyncio
async def test_multiple_projects(storage, sample_character_data):
    character_name = "角色"
    
    await storage.save_character("project1", character_name, sample_character_data)
    await storage.save_character("project2", character_name, sample_character_data)
    
    data1 = await storage.load_character("project1", character_name)
    data2 = await storage.load_character("project2", character_name)
    
    assert data1 is not None
    assert data2 is not None
