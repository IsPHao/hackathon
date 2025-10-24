from typing import Dict, List, Optional, Any
import asyncio
import logging
import uuid
import aiohttp
from datetime import datetime

from openai import AsyncOpenAI

from .config import ImageGeneratorConfig
from .storage import create_storage, StorageBackend
from .exceptions import ValidationError, GenerationError, APIError

logger = logging.getLogger(__name__)


class ImageGeneratorAgent:
    
    def __init__(
        self,
        openai_client: AsyncOpenAI,
        config: Optional[ImageGeneratorConfig] = None,
        storage: Optional[StorageBackend] = None,
    ):
        self.config = config or ImageGeneratorConfig()
        self.client = openai_client
        
        if storage:
            self.storage = storage
        else:
            self.storage = create_storage(
                storage_type=self.config.storage_type,
                base_path=self.config.local_storage_path,
                bucket=self.config.oss_bucket,
                endpoint=self.config.oss_endpoint,
                access_key=self.config.oss_access_key,
                secret_key=self.config.oss_secret_key,
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
                image_data = await self._download_image(image_url)
                
                filename = self._generate_filename(scene)
                stored_url = await self.storage.save(image_data, filename)
                
                logger.info(f"Successfully generated and stored image: {stored_url}")
                return stored_url
            
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
    
    async def _download_image(self, url: str) -> bytes:
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise GenerationError(f"Failed to download image: HTTP {response.status}")
                    
                    image_data = await response.read()
                    
                    if len(image_data) < 1024:
                        raise GenerationError("Downloaded image is too small")
                    
                    return image_data
        
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            raise GenerationError(f"Failed to download image: {e}") from e
    
    def _generate_filename(self, scene: Dict[str, Any]) -> str:
        scene_id = scene.get("scene_id", scene.get("id", str(uuid.uuid4())))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"scene_{scene_id}_{timestamp}.png"
    
    def _validate_scene(self, scene: Dict[str, Any]):
        if not isinstance(scene, dict):
            raise ValidationError("Scene must be a dictionary")
        
        if "image_prompt" not in scene and "description" not in scene:
            raise ValidationError("Scene must have 'image_prompt' or 'description'")
