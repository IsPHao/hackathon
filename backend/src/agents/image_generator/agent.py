from typing import Dict, List, Optional, Any
import asyncio
import logging
import uuid
import aiohttp
from datetime import datetime

from openai import AsyncOpenAI

from .config import ImageGeneratorConfig
from ..base import TaskStorageManager, download_to_bytes
from .exceptions import ValidationError, GenerationError, APIError

logger = logging.getLogger(__name__)


class ImageGeneratorAgent:
    """
    图像生成Agent
    
    负责根据场景描述和角色信息生成图像。
    支持批量生成和重试机制。
    
    Attributes:
        llm: 语言模型客户端
        openai_client: OpenAI API客户端
        storage: 存储管理器
        config: 配置对象
    """
    
    def __init__(
        self,
        openai_client: AsyncOpenAI,
        task_id: str,
        config: Optional[ImageGeneratorConfig] = None,
    ):
        self.config = config or ImageGeneratorConfig()
        self.client = openai_client
        self.task_storage = TaskStorageManager(
            task_id,
            base_path=self.config.task_storage_base_path
        )
    
    async def generate(
        self,
        scene: Dict[str, Any],
        character_templates: Optional[Dict[str, Any]] = None,
    ) -> str:
        self._validate_scene(scene)
        
        prompt = self._build_prompt(scene, character_templates or {})
        
        for attempt in range(self.config.retry_attempts):
            try:
                image_url = await self._generate_image(prompt)
                image_data = await download_to_bytes(image_url, timeout=self.config.timeout)
                
                filename = self._generate_filename(scene)
                stored_path = await self.task_storage.save_image(image_data, filename)
                
                logger.info(f"Successfully generated and stored image: {stored_path}")
                return stored_path
            
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{self.config.retry_attempts} failed: {e}")
                if attempt == self.config.retry_attempts - 1:
                    raise GenerationError(f"Failed to generate image after {self.config.retry_attempts} attempts") from e
                await asyncio.sleep(2 ** attempt)
        
        raise GenerationError("Failed to generate image")
    
    async def generate_batch(
        self,
        scenes: List[Dict[str, Any]],
        character_templates: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        results = []
        batch_size = self.config.batch_size
        
        for i in range(0, len(scenes), batch_size):
            batch = scenes[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}/{(len(scenes) + batch_size - 1) // batch_size}")
            
            batch_tasks = [
                self.generate(scene, character_templates)
                for scene in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch generation failed: {result}")
                    results.append("")
                else:
                    results.append(result)
            
            if i + batch_size < len(scenes):
                await asyncio.sleep(1)
        
        return results
    
    def _build_prompt(
        self,
        scene: Dict[str, Any],
        character_templates: Dict[str, Any],
    ) -> str:
        base_prompt = scene.get("image_prompt", scene.get("description", ""))
        
        if not base_prompt:
            raise ValidationError("Scene must have 'image_prompt' or 'description'")
        
        character_prompts = []
        for char_name in scene.get("characters", []):
            if char_name in character_templates:
                char_template = character_templates[char_name]
                if isinstance(char_template, dict):
                    char_prompt = char_template.get("base_prompt", char_template.get("visual_description", ""))
                else:
                    char_prompt = str(char_template)
                
                if char_prompt:
                    character_prompts.append(char_prompt)
        
        if character_prompts:
            full_prompt = f"{base_prompt}, characters: {', '.join(character_prompts)}"
        else:
            full_prompt = base_prompt
        
        style_suffix = ", anime style, high quality"
        full_prompt = f"{full_prompt}{style_suffix}"
        
        return full_prompt
    
    async def _generate_image(self, prompt: str) -> str:
        try:
            response = await self.client.images.generate(
                model=self.config.model,
                prompt=prompt,
                size=self.config.size,
                quality=self.config.quality,
                n=self.config.n,
            )
            
            if not response.data:
                raise GenerationError("No image generated")
            
            image_url = response.data[0].url
            if not image_url:
                raise GenerationError("No image URL in response")
            
            return image_url
        
        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            raise APIError(f"Image generation API error: {e}") from e
    
    def _generate_filename(self, scene: Dict[str, Any]) -> str:
        scene_id = scene.get("scene_id", scene.get("id", str(uuid.uuid4())))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"scene_{scene_id}_{timestamp}.png"
    
    def _validate_scene(self, scene: Dict[str, Any]):
        if not isinstance(scene, dict):
            raise ValidationError("Scene must be a dictionary")
        
        if "image_prompt" not in scene and "description" not in scene:
            raise ValidationError("Scene must have 'image_prompt' or 'description'")
