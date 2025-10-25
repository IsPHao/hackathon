from typing import Dict, List, Any, Optional
import json
import hashlib
import logging
import time

from langchain_openai import ChatOpenAI

from .config import CharacterConsistencyConfig
from .exceptions import ValidationError, GenerationError, StorageError
from .storage import StorageInterface, LocalFileStorage
from .prompts import CHARACTER_FEATURE_EXTRACTION_PROMPT_TEMPLATE, SCENE_PROMPT_TEMPLATE
from ..base.llm_utils import LLMJSONMixin
from ..base.agent import BaseAgent

logger = logging.getLogger(__name__)


class CharacterTemplate:
    """
    角色模板类
    
    封装角色的基础信息、特征和提示词,用于生成一致性的角色图像。
    
    Attributes:
        name: 角色名称
        base_prompt: 基础提示词,描述角色的外貌特征
        negative_prompt: 负面提示词,避免不期望的特征
        features: 角色特征详情
        reference_image_url: 参考图像URL
        seed: 随机种子,用于生成一致性图像
    """
    
    def __init__(self, character_data: Dict[str, Any]):
        self.name = character_data.get("name", "")
        self.base_prompt = character_data.get("base_prompt", "")
        self.negative_prompt = character_data.get("negative_prompt", "low quality, blurry, distorted")
        self.features = character_data.get("features", {})
        self.reference_image_url = character_data.get("reference_image_url")
        self.seed = self._generate_seed(self.name)
    
    def _generate_seed(self, name: str) -> int:
        """
        从角色名称生成稳定的随机种子
        
        使用SHA256哈希以降低冲突风险。
        
        Args:
            name: 角色名称
        
        Returns:
            int: 32位无符号整数种子值
        """
        hash_val = int(hashlib.sha256(name.encode('utf-8')).hexdigest(), 16)
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


class CharacterConsistencyAgent(BaseAgent[CharacterConsistencyConfig], LLMJSONMixin):
    """
    角色一致性管理Agent
    
    负责提取角色特征、管理角色模板、并为图像生成提供一致性的提示词。
    支持角色模板的存储和加载。
    
    Attributes:
        llm: 语言模型客户端
        config: 配置对象
        storage: 存储接口
        character_cache: 角色模板缓存
    """
    
    def __init__(
        self,
        llm: ChatOpenAI,
        storage: Optional[StorageInterface] = None,
        config: Optional[CharacterConsistencyConfig] = None,
    ):
        super().__init__(config)
        self.llm = llm
        self.storage = storage or LocalFileStorage(self.config.storage_base_path)
        self.cache: Dict[str, CharacterTemplate] = {}
        self._cache_timestamps: Dict[str, float] = {}
    
    def _default_config(self) -> CharacterConsistencyConfig:
        return CharacterConsistencyConfig()
    
    async def execute(self, characters: List[Dict[str, Any]], project_id: str, **kwargs) -> Dict[str, CharacterTemplate]:
        """
        执行角色一致性管理(统一接口)
        
        Args:
            characters: 角色列表
            project_id: 项目id
            **kwargs: 其他参数
        
        Returns:
            Dict[str, CharacterTemplate]: 角色模板字典
        """
        return await self.manage(characters, project_id)
    
    async def health_check(self) -> bool:
        """健康检查:测试LLM连接和存储"""
        try:
            # 测试LLM
            test_messages = [("user", "test")]
            await self.llm.ainvoke(test_messages)
            # 测试存储
            if hasattr(self.storage, 'health_check'):
                storage_ok = await self.storage.health_check()
                if not storage_ok:
                    raise Exception("Storage health check failed")
            self.logger.info("CharacterConsistencyAgent health check: OK")
            return True
        except Exception as e:
            self.logger.error(f"CharacterConsistencyAgent health check failed: {e}")
            return False
    
    async def manage(
        self,
        characters: List[Dict[str, Any]],
        project_id: str,
    ) -> Dict[str, CharacterTemplate]:
        self._validate_input(characters, project_id)
        
        character_templates = {}
        failed_characters = []
        
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
                failed_characters.append(character_name)
        
        if failed_characters:
            raise GenerationError(
                f"Failed to process {len(failed_characters)} character(s): {', '.join(failed_characters)}"
            )
        
        return character_templates
    
    async def _get_or_create_character(
        self,
        project_id: str,
        character_name: str,
        character_data: Dict[str, Any],
    ) -> CharacterTemplate:
        cache_key = f"{project_id}:{character_name}"
        
        if self.config.enable_caching and cache_key in self.cache:
            cache_age = time.time() - self._cache_timestamps.get(cache_key, 0)
            if cache_age < 3600:
                logger.info(f"Using cached character template for {character_name}")
                return self.cache[cache_key]
            else:
                logger.info(f"Cache expired for {character_name}, refreshing")
                del self.cache[cache_key]
                del self._cache_timestamps[cache_key]
        
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
            self._cache_timestamps[cache_key] = time.time()
        
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
        
        variables = {
            "name": name,
            "description": description,
            "appearance": json.dumps(appearance, ensure_ascii=False)
        }
        
        try:
            features_data = await self._call_llm_json(
                CHARACTER_FEATURE_EXTRACTION_PROMPT_TEMPLATE,
                variables=variables,
                parse_error_class=GenerationError,
                api_error_class=GenerationError
            )
            return features_data
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
