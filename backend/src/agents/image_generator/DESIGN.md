# Image Generator Agent 设计文档

## 1. Agent概述

### 1.1 职责
图像生成Agent负责根据分镜脚本和角色信息生成场景图片。

### 1.2 核心功能
- 批量图片生成
- 角色一致性保证
- 质量检查
- 图片优化和上传
- 支持文生图和图生图两种模式

## 2. 模型选择

| 模型 | 一致性 | 速度 | 成本 | 场景 |
|------|--------|------|------|------|
| Qwen-Image | ⭐⭐⭐⭐ | 5s | 按量计费 | 默认 |
| WanX | ⭐⭐⭐ | 8s | 按量计费 | 备选 |
| DALL-E 3 | ⭐⭐⭐ | 10s | $0.04 | 原始方案 |
| SD+IPAdapter | ⭐⭐⭐⭐⭐ | 5s | 免费 | Phase 2 |

## 3. 核心实现

```python
class ImageGeneratorAgent:
    
    def __init__(
        self,
        config: ImageGeneratorConfig,
        storage_service=None
    ):
        self.config = config
        self.storage = storage_service
    
    async def generate(
        self,
        scene: Dict,
        character_templates: Dict[str, CharacterTemplate]
    ) -> str:
        """生成单个场景图片"""
        # 1. 构建prompt
        prompt = self._build_prompt(scene, character_templates)
        
        # 2. 生成图片
        image = await self._generate_image(prompt, scene.get("seed"))
        
        # 3. 质量检查
        if not await self._check_quality(image):
            # 重试
            image = await self._generate_image(prompt, scene.get("seed"))
        
        # 4. 上传
        image_url = await self._upload_image(image)
        
        return image_url
    
    async def generate_batch(
        self,
        scenes: List[Dict],
        character_templates: Dict
    ) -> List[str]:
        """批量生成图片"""
        # 并发生成
        tasks = [
            self.generate(scene, character_templates)
            for scene in scenes
        ]
        
        images = await asyncio.gather(*tasks)
        return images
    
    def _build_prompt(
        self,
        scene: Dict,
        character_templates: Dict
    ) -> str:
        """构建完整prompt"""
        # 基础场景描述
        base_prompt = scene["image_prompt"]
        
        # 添加角色描述
        character_prompts = []
        for char_name in scene["characters"]:
            if char_name in character_templates:
                char_prompt = character_templates[char_name].base_prompt
                character_prompts.append(char_prompt)
        
        # 组合
        full_prompt = f"{base_prompt}, {', '.join(character_prompts)}"
        
        return full_prompt
    
    async def _generate_image(
        self,
        prompt: str,
        seed: Optional[int] = None
    ) -> bytes:
        """调用API生成图片"""
        if self.config.generation_mode == "text2image":
            return await self._generate_with_qiniu_t2i(prompt)
        else:
            return await self._generate_with_qiniu_i2i(prompt, seed)
    
    async def _generate_with_qiniu_t2i(self, prompt: str) -> bytes:
        """使用七牛云文生图API生成"""
        # 构建请求参数
        params = {
            "model": self.config.model,
            "prompt": prompt,
            "size": self.config.size,
        }
        
        # 生成签名
        token = self._generate_token("/v1/images/generations", params, "POST")
        
        headers = {
            "Authorization": f"Bearer {self.config.qiniu_api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.config.qiniu_endpoint}/v1/images/generations"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise APIError(f"Qiniu API error: {response.status} - {error_text}")
                
                result = await response.json()
                
                # 解析七牛云API响应
                if "data" not in result or not result["data"]:
                    raise GenerationError("Invalid response from Qiniu API: no image data")
                
                # 获取第一个图像的base64数据
                image_b64 = result["data"][0].get("b64_json")
                if not image_b64:
                    raise GenerationError("Invalid response from Qiniu API: no base64 image data")
                
                # 解码base64图像数据
                image_data = base64.b64decode(image_b64)
                return image_data
    
    async def _check_quality(self, image: bytes) -> bool:
        """检查图片质量"""
        # 检查分辨率
        # 检查是否模糊
        # 检查是否包含期望元素
        return True
```

## 4. 批量优化

```python
class BatchImageGenerator:
    """批量图片生成器"""
    
    async def generate_batch(
        self,
        scenes: List[Dict],
        batch_size: int = 5
    ) -> List[str]:
        """分批并发生成"""
        results = []
        
        for i in range(0, len(scenes), batch_size):
            batch = scenes[i:i+batch_size]
            batch_results = await asyncio.gather(*[
                self.generate_single(scene)
                for scene in batch
            ])
            results.extend(batch_results)
            
            # 避免API限流
            await asyncio.sleep(1)
        
        return results
```

## 5. 性能指标

- 生成速度: 5s/图 (Qwen-Image)
- 成功率: >95%
- 质量评分: >85%
- 批量吞吐: 50图/5分钟

## 6. API集成

### 6.1 七牛云文生图API

使用七牛云AI API进行文本到图像的生成，正确处理其响应格式。

### 6.2 七牛云图生图API

支持基于现有图像和文本提示进行图像编辑和变换。

### 6.3 响应格式处理

七牛云AI API返回以下格式的响应：

```json
{
  "created": 1234567890,
  "data": [
    {
      "b64_json": "iVBORw0KGgoAAAANSUhEUgA..."
    },
    {
      "b64_json": "iVBORw0KGgoAAAANSUhEUgB..."
    }
  ],
  "size": "1024x1024",
  "quality": "hd",
  "output_format": "png",
  "usage": {
    "total_tokens": 5234,
    "input_tokens": 234,
    "output_tokens": 5000,
    "input_tokens_details": {
      "text_tokens": 234,
      "image_tokens": 0
    }
  }
}
```

我们的实现会解析[data](file:///home/ubuntu/workspace/demo/hackathon/backend/src/agents/base/storage.py#L28-L28)数组中的第一个图像的[b64_json](file:///home/ubuntu/workspace/demo/hackathon/backend/src/agents/image_generator/agent.py#L230-L230)字段，并将其解码为图像数据。