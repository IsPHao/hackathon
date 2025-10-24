import json
import os
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path
from abc import ABC, abstractmethod

from .exceptions import StorageError


class StorageInterface(ABC):
    
    @abstractmethod
    async def save_character(self, project_id: str, character_name: str, data: Dict[str, Any]) -> str:
        pass
    
    @abstractmethod
    async def load_character(self, project_id: str, character_name: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def character_exists(self, project_id: str, character_name: str) -> bool:
        pass
    
    @abstractmethod
    async def save_reference_image(self, project_id: str, character_name: str, image_url: str) -> str:
        pass


class LocalFileStorage(StorageInterface):
    
    def __init__(self, base_path: str = "data/characters"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_character_dir(self, project_id: str) -> Path:
        project_dir = self.base_path / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir
    
    def _get_character_file(self, project_id: str, character_name: str) -> Path:
        safe_name = self._sanitize_filename(character_name)
        return self._get_character_dir(project_id) / f"{safe_name}.json"
    
    def _sanitize_filename(self, name: str) -> str:
        return hashlib.md5(name.encode()).hexdigest()[:16]
    
    async def save_character(self, project_id: str, character_name: str, data: Dict[str, Any]) -> str:
        try:
            file_path = self._get_character_file(project_id, character_name)
            
            data_to_save = {
                "name": character_name,
                **data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            
            return str(file_path)
        
        except Exception as e:
            raise StorageError(f"Failed to save character: {e}") from e
    
    async def load_character(self, project_id: str, character_name: str) -> Optional[Dict[str, Any]]:
        try:
            file_path = self._get_character_file(project_id, character_name)
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        except Exception as e:
            raise StorageError(f"Failed to load character: {e}") from e
    
    async def character_exists(self, project_id: str, character_name: str) -> bool:
        file_path = self._get_character_file(project_id, character_name)
        return file_path.exists()
    
    async def save_reference_image(self, project_id: str, character_name: str, image_url: str) -> str:
        try:
            character_data = await self.load_character(project_id, character_name)
            
            if character_data is None:
                raise StorageError(f"Character {character_name} not found")
            
            character_data["reference_image_url"] = image_url
            
            await self.save_character(project_id, character_name, character_data)
            
            return image_url
        
        except Exception as e:
            raise StorageError(f"Failed to save reference image: {e}") from e
