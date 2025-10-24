from typing import Dict, List, Any, Optional
import json
import hashlib
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .config import CharacterConsistencyConfig
from .exceptions import ValidationError, GenerationError, StorageError
from .storage import StorageInterface, LocalFileStorage
from .prompts import CHARACTER_FEATURE_EXTRACTION_PROMPT, SCENE_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class CharacterTemplate:
    
    def __init__(self, character_data: Dict[str, Any]):
        self.name = character_data.get("name", "")
        self.base_prompt = character_data.get("base_prompt", "")
        self.negative_prompt = character_data.get("negative_prompt", "low quality, blurry, distorted")
        self.features = character_data.get("features", {})
        self.reference_image_url = character_data.get("reference_image_url")
        self.seed = self._generate_seed(self.name)
    
    def _generate_seed(self, name: str) -> int:
        hash_val = int(hashlib.md5(name.encode()).hexdigest(), 16)
        return hash_val % (2**32)
    
    def create_scene_prompt(self, scene_context: str) -> str:
        return SCENE_PROMPT_TEMPLATE.format(
            base_prompt=self.base_prompt,
            scene_context=scene_context
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "base_prompt": self.base_prompt,
            "negative_prompt": self.negative_prompt,
            "features": self.features,
            "reference_image_url": self.reference_image_url,
            "seed": self.seed,
        }


class CharacterConsistencyAgent:
    
    def __init__(
        self,
        llm: ChatOpenAI,
        storage: Optional[StorageInterface] = None,
        config: Optional[CharacterConsistencyConfig] = None,
    ):
        self.llm = llm
        self.config = config or CharacterConsistencyConfig()
        self.storage = storage or LocalFileStorage(self.config.storage_base_path)
        self.cache: Dict[str, CharacterTemplate] = {}
    
    async def manage(
        self,
        characters: List[Dict[str, Any]],
        project_id: str,
    ) -> Dict[str, CharacterTemplate]:
        self._validate_input(characters, project_id)
        
        character_templates = {}
        
        for char in characters:
            character_name = char.get("name")
            
            if not character_name:
                logger.warning("Skipping character without name")
                continue
            
            try:
                template = await self._get_or_create_character(
                    project_id,
                    character_name,
                    char
                )
                
                character_templates[character_name] = template
                
            except Exception as e:
                logger.error(f"Failed to process character {character_name}: {e}")
                raise
        
        return character_templates
    
    async def _get_or_create_character(
        self,
        project_id: str,
        character_name: str,
        character_data: Dict[str, Any],
    ) -> CharacterTemplate:
        cache_key = f"{project_id}:{character_name}"
        
        if self.config.enable_caching and cache_key in self.cache:
            logger.info(f"Using cached character template for {character_name}")
            return self.cache[cache_key]
        
        existing_data = await self.storage.load_character(project_id, character_name)
        
        if existing_data:
            logger.info(f"Loaded existing character {character_name} from storage")
            template = CharacterTemplate(existing_data)
        else:
            logger.info(f"Creating new character template for {character_name}")
            template = await self._create_character_template(
                project_id,
                character_name,
                character_data
            )
        
        if self.config.enable_caching:
            self.cache[cache_key] = template
        
        return template
    
    async def _create_character_template(
        self,
        project_id: str,
        character_name: str,
        character_data: Dict[str, Any],
    ) -> CharacterTemplate:
        features = await self._extract_character_features(character_data)
        
        base_prompt = self._build_base_prompt(features)
        
        template_data = {
            "name": character_name,
            "base_prompt": base_prompt,
            "negative_prompt": features.get("negative_prompt", "low quality, blurry, distorted"),
            "features": features.get("features", {}),
            "reference_image_url": None,
        }
        
        await self.storage.save_character(project_id, character_name, template_data)
        
        return CharacterTemplate(template_data)
    
    async def _extract_character_features(
        self,
        character_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        name = character_data.get("name", "Unknown")
        description = character_data.get("description", "")
        appearance = character_data.get("appearance", {})
        
        prompt = CHARACTER_FEATURE_EXTRACTION_PROMPT.format(
            name=name,
            description=description,
            appearance=json.dumps(appearance, ensure_ascii=False)
        )
        
        try:
            messages = [
                ("system", "You are a professional character design expert."),
                ("human", prompt),
            ]
            
            response = await self.llm.ainvoke(
                messages,
                response_format={"type": "json_object"},
            )
            
            features_data = json.loads(response.content)
            return features_data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise GenerationError(f"Invalid JSON response: {e}") from e
        
        except Exception as e:
            logger.error(f"Failed to extract character features: {e}")
            raise GenerationError(f"Failed to extract character features: {e}") from e
    
    def _build_base_prompt(self, features_data: Dict[str, Any]) -> str:
        base_prompt = features_data.get("base_prompt", "")
        
        if not base_prompt and "features" in features_data:
            features = features_data["features"]
            parts = [
                "anime style",
                features.get("gender", ""),
                f"{features.get('age', '')} years old" if features.get("age") else "",
                features.get("hair", ""),
                features.get("eyes", ""),
                features.get("clothing", ""),
                features.get("distinctive_features", ""),
                self.config.reference_image_prompt_suffix,
            ]
            base_prompt = ", ".join([p for p in parts if p])
        
        return base_prompt
    
    async def save_reference_image(
        self,
        project_id: str,
        character_name: str,
        image_url: str,
    ) -> None:
        try:
            await self.storage.save_reference_image(project_id, character_name, image_url)
            
            cache_key = f"{project_id}:{character_name}"
            if cache_key in self.cache:
                self.cache[cache_key].reference_image_url = image_url
            
            logger.info(f"Saved reference image for {character_name}")
        
        except Exception as e:
            logger.error(f"Failed to save reference image: {e}")
            raise StorageError(f"Failed to save reference image: {e}") from e
    
    def _validate_input(self, characters: List[Dict[str, Any]], project_id: str):
        if not project_id:
            raise ValidationError("project_id is required")
        
        if not characters:
            raise ValidationError("characters list cannot be empty")
        
        if not isinstance(characters, list):
            raise ValidationError("characters must be a list")
