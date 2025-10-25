from typing import Dict, List, Optional, Any, cast
import asyncio
import logging
import uuid
from datetime import datetime
import base64
import json
import hashlib
import hmac
import time
import urllib.parse
from urllib.parse import urlencode

import aiohttp
from aiohttp import ClientTimeout

from .config import ImageGeneratorConfig
from ..base import TaskStorageManager, download_to_bytes
from ..base.agent import BaseAgent
from ..base.exceptions import ValidationError, GenerationError, APIError

logger = logging.getLogger(__name__)


class ImageGeneratorAgent(BaseAgent[ImageGeneratorConfig]):
    """
    图像生成Agent
    
    负责根据场景描述和角色信息生成图像。
    支持批量生成和重试机制。
    支持七牛云文生图和图生图功能。
    
    Attributes:
        config: 配置对象
        task_storage: 存储管理器
    """
    
    def __init__(
        self,
        task_id: str,
        config: Optional[ImageGeneratorConfig] = None,
    ):
        super().__init__(config)
        self.task_id = task_id
        self.task_storage = TaskStorageManager(
            task_id,
            base_path=config.task_storage_base_path if config else "./data/tasks"
        )
    
    def _default_config(self) -> ImageGeneratorConfig:
        return ImageGeneratorConfig()
    
    async def execute(self, scene: Dict[str, Any], character_templates: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """
        执行图像生成(统一接口)
        
        Args:
            scene: 场景描述
            character_templates: 角色模板
            **kwargs: 其他参数
        
        Returns:
            str: 图像路径
        """
        return await self.generate(scene, character_templates)
    
    async def health_check(self) -> bool:
        """健康检查:测试七牛云API连接"""
        try:
            # 生成一个测试用的简单提示词
            test_prompt = "a simple blue square"
            await self._generate_image_qiniu(test_prompt)
            self.logger.info("ImageGeneratorAgent health check: OK")
            return True
        except Exception as e:
            self.logger.error(f"ImageGeneratorAgent health check failed: {e}")
            return False
    
    async def generate(
        self,
        scene: Dict[str, Any],
        character_templates: Optional[Dict[str, Any]] = None,
        reference_image: Optional[bytes] = None,
    ) -> str:
        self._validate_scene(scene)
        
        prompt = self._build_prompt(scene, character_templates or {})
        
        config = cast(ImageGeneratorConfig, self.config)
        for attempt in range(config.retry_attempts):
            try:
                if config.generation_mode == "text2image" or reference_image is None:
                    image_data = await self._generate_image_qiniu(prompt)
                else:  # image2image
                    image_data = await self._generate_image_qiniu_i2i(prompt, reference_image)
                
                filename = self._generate_filename(scene)
                stored_path = await self.task_storage.save_image(image_data, filename)
                
                logger.info(f"Successfully generated and stored image: {stored_path}")
                return stored_path
            
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{config.retry_attempts} failed: {e}")
                if attempt == config.retry_attempts - 1:
                    raise GenerationError(f"Failed to generate image after {config.retry_attempts} attempts") from e
                await asyncio.sleep(2 ** attempt)
        
        raise GenerationError("Failed to generate image")
    
    async def generate_batch(
        self,
        scenes: List[Dict[str, Any]],
        character_templates: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        results = []
        config = cast(ImageGeneratorConfig, self.config)
        batch_size = config.batch_size
        failed_scenes = []
        
        for i in range(0, len(scenes), batch_size):
            batch = scenes[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}/{(len(scenes) + batch_size - 1) // batch_size}")
            
            batch_tasks = [
                self.generate(scene, character_templates)
                for scene in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    scene_id = batch[idx].get("scene_id", idx + i)
                    logger.error(f"Failed to generate image for scene {scene_id}: {result}")
                    failed_scenes.append(scene_id)
                    results.append("")
                else:
                    results.append(result)
            
            if i + batch_size < len(scenes):
                await asyncio.sleep(1)
        
        if failed_scenes:
            raise GenerationError(
                f"Failed to generate images for {len(failed_scenes)} scene(s): {failed_scenes}"
            )
        
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
    
    async def _generate_image_qiniu(self, prompt: str) -> bytes:
        """
        使用七牛云API生成图像(文生图)
        
        Args:
            prompt: 图像生成提示词
            
        Returns:
            bytes: 图像数据
        """
        try:
            config = cast(ImageGeneratorConfig, self.config)
            # 准备请求参数
            params = {
                "model": config.model,
                "prompt": prompt,
                "size": config.size,
            }
            
            # 生成签名
            token = self._generate_token("/v1/images/generations", params, "POST")
            
            headers = {
                "Authorization": f"Bearer {config.qiniu_api_key}",
                "Content-Type": "application/json"
            }
            
            url = f"{config.qiniu_endpoint}/v1/images/generations"
            
            timeout = ClientTimeout(total=config.timeout)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params, headers=headers, timeout=timeout) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise APIError(f"Qiniu API error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    
                    # 根据七牛云API文档解析响应
                    if "data" not in result or not result["data"]:
                        raise GenerationError("Invalid response from Qiniu API: no image data")
                    
                    # 获取第一个图像的base64数据
                    image_b64 = result["data"][0].get("b64_json")
                    if not image_b64:
                        raise GenerationError("Invalid response from Qiniu API: no base64 image data")
                    
                    # 解码base64图像数据
                    image_data = base64.b64decode(image_b64)
                    return image_data
        
        except Exception as e:
            logger.error(f"Failed to generate image with Qiniu: {e}")
            raise APIError(f"Image generation API error: {e}") from e
    
    async def _generate_image_qiniu_i2i(self, prompt: str, reference_image: bytes) -> bytes:
        """
        使用七牛云API生成图像(图生图)
        
        Args:
            prompt: 图像生成提示词
            reference_image: 参考图像数据
            
        Returns:
            bytes: 图像数据
        """
        try:
            config = cast(ImageGeneratorConfig, self.config)
            # 将参考图像转换为base64
            image_base64 = base64.b64encode(reference_image).decode('utf-8')
            
            # 准备请求参数
            params = {
                "model": config.model,
                "prompt": prompt,
                "image": image_base64,
                "size": config.size,
            }
            
            # 生成签名
            token = self._generate_token("/v1/images/generations", params, "POST")
            
            headers = {
                "Authorization": f"Bearer {config.qiniu_api_key}",
                "Content-Type": "application/json"
            }
            
            url = f"{config.qiniu_endpoint}/v1/images/generations"
            
            timeout = ClientTimeout(total=config.timeout)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params, headers=headers, timeout=timeout) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise APIError(f"Qiniu API error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    
                    # 根据七牛云API文档解析响应
                    if "data" not in result or not result["data"]:
                        raise GenerationError("Invalid response from Qiniu API: no image data")
                    
                    # 获取第一个图像的base64数据
                    image_b64 = result["data"][0].get("b64_json")
                    if not image_b64:
                        raise GenerationError("Invalid response from Qiniu API: no base64 image data")
                    
                    # 解码base64图像数据
                    image_data = base64.b64decode(image_b64)
                    return image_data
        
        except Exception as e:
            logger.error(f"Failed to generate image with Qiniu (image2image): {e}")
            raise APIError(f"Image generation API error: {e}") from e
    
    def _generate_token(self, path: str, params: Dict[str, Any], method: str) -> str:
        """
        生成七牛云API Token
        
        Args:
            path: API路径
            params: 请求参数
            method: HTTP方法
            
        Returns:
            str: 签名Token
        """
        config = cast(ImageGeneratorConfig, self.config)
        # 构建待签名字符串
        if method == "GET":
            url_params = urlencode(sorted(params.items()))
            signing_str = f"{method} {path}"
            if url_params:
                signing_str += f"?{url_params}"
            signing_str += "\nHost: openai.qiniu.com\n\n"
        else:
            url_params = json.dumps(params, separators=(',', ':'))
            signing_str = f"{method} {path}\nHost: openai.qiniu.com\nContent-Type: application/json\n\n{url_params}"
        
        # 使用HMAC-SHA1算法签名
        signature = hmac.new(
            config.qiniu_api_key.encode('utf-8'),
            signing_str.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        # Base64编码
        encoded_signature = base64.b64encode(signature).decode('utf-8')
        encoded_api_key = base64.b64encode(config.qiniu_api_key.encode('utf-8')).decode('utf-8')
        
        return f"{encoded_api_key}:{encoded_signature}"
    
    def _generate_filename(self, scene: Dict[str, Any]) -> str:
        scene_id = scene.get("scene_id", scene.get("id", str(uuid.uuid4())))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"scene_{scene_id}_{timestamp}.png"
    
    def _validate_scene(self, scene: Dict[str, Any]):
        if not isinstance(scene, dict):
            raise ValidationError("Scene must be a dictionary")
        
        image_prompt = scene.get("image_prompt", "")
        description = scene.get("description", "")
        
        # Check if both image_prompt and description are missing or empty
        if not image_prompt and not description:
            raise ValidationError("Scene must have 'image_prompt' or 'description'")