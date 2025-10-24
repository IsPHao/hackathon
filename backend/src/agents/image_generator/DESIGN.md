# Image Generator Agent 设计文档

## 1. Agent概述

### 1.1 职责
图像生成Agent负责根据分镜脚本和角色信息生成场景图片。

### 1.2 核心功能
- 批量图片生成
- 角色一致性保证
- 质量检查
- 图片优化和上传

## 2. 模型选择

| 模型 | 一致性 | 速度 | 成本 | 场景 |
|------|--------|------|------|------|
| DALL-E 3 | ⭐⭐⭐ | 10s | $0.04 | Phase 1 |
| SD+IPAdapter | ⭐⭐⭐⭐⭐ | 5s | 免费 | Phase 2 |
| Flux.1 | ⭐⭐⭐⭐ | 8s | 免费 | 开源 |

## 3. 核心实现

```python
class ImageGeneratorAgent:
    
    def __init__(
        self,
        dalle_client=None,
        sd_client=None,
        storage_service=None
    ):
        self.dalle_client = dalle_client
        self.sd_client = sd_client
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
        if self.dalle_client:
            return await self._generate_with_dalle(prompt)
        elif self.sd_client:
            return await self._generate_with_sd(prompt, seed)
    
    async def _generate_with_dalle(self, prompt: str) -> bytes:
        """使用DALL-E 3生成"""
        response = await self.dalle_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        image_url = response.data[0].url
        # 下载图片
        image_data = await self._download_image(image_url)
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

- 生成速度: 10s/图 (DALL-E 3)
- 成功率: >95%
- 质量评分: >85%
- 批量吞吐: 30图/5分钟
