# SceneRenderer 模块设计文档

## 1. 模块概述

SceneRenderer 负责渲染场景，为每个分镜场景生成对应的图片和音频资源。

### 1.1 职责
- 接收 StoryboardResult 作为输入
- 为每个场景生成图片（通过七牛云图像生成API）
- 为每个场景生成音频（通过七牛云TTS API）
- 返回 RenderResult，包含所有渲染完成的场景

### 1.2 输入输出

**输入**: `StoryboardResult`
- 包含章节列表和场景列表
- 每个场景包含图像提示词、音频文本、角色信息等

**输出**: `RenderResult`
- 包含所有章节的渲染结果
- 每个场景包含生成的图片路径和音频路径

## 2. 核心功能

### 2.1 场景图片生成

使用七牛云图像生成API，根据场景的图像提示词生成图片。

```python
async def _generate_image(self, scene: StoryboardScene) -> str:
    prompt = self._build_image_prompt(scene)
    image_data = await self._call_image_generation_api(prompt)
    image_path = await self.task_storage.save_image(image_data, filename)
    return image_path
```

**图像提示词构建**:
- 基础提示词: scene.image.prompt 或 scene.description
- 风格标签: scene.image.style_tags
- 镜头类型: scene.image.shot_type
- 相机角度: scene.image.camera_angle
- 构图: scene.image.composition
- 光照: scene.image.lighting

### 2.2 场景音频生成

使用七牛云TTS API，根据场景的音频文本生成语音。

```python
async def _generate_audio(self, scene: StoryboardScene) -> str:
    text = scene.audio.text
    voice_type = self._select_voice_type(scene)
    audio_data = await self._call_tts_api(text, voice_type)
    audio_path = await self.task_storage.save_audio(audio_data, filename)
    return audio_path
```

**音色选择逻辑**:
- 如果是旁白 (narration): 使用默认旁白音色
- 如果是对话 (dialogue): 根据角色信息匹配合适的音色
  - 匹配维度: 性别、年龄段
  - 年龄段分类: child (儿童), young (青年), adult (成人), elder (老年)

### 2.3 角色音色缓存

为同一个角色分配固定的音色，保持音色一致性。

```python
self.character_voice_cache: Dict[str, str] = {}

def _prepare_character_voices(self, storyboard: StoryboardResult):
    for chapter in storyboard.chapters:
        for scene in chapter.scenes:
            if scene.audio.type == "dialogue" and scene.audio.speaker:
                # 为角色分配音色并缓存
                voice_type = self._match_voice_by_character(character)
                self.character_voice_cache[speaker] = voice_type
```

## 3. 数据模型

### 3.1 输入模型: StoryboardScene

```python
class StoryboardScene:
    scene_id: str
    chapter_id: int
    description: str
    location: str
    time: str
    atmosphere: str
    duration: float
    characters: List[CharacterRenderInfo]
    audio: AudioInfo
    image: ImageRenderInfo
```

### 3.2 输出模型: RenderedScene

```python
class RenderedScene:
    scene_id: str
    chapter_id: int
    image_path: str
    audio_path: str
    duration: float
    audio_duration: float
    metadata: Dict[str, Any]
```

## 4. 错误处理

### 4.1 重试机制

图片和音频生成都有重试机制，默认最多重试3次。

```python
for attempt in range(self.config.retry_attempts):
    try:
        # 生成图片/音频
        return result
    except Exception as e:
        if attempt == self.config.retry_attempts - 1:
            raise GenerationError(...)
        await asyncio.sleep(2 ** attempt)
```

### 4.2 降级策略

- 图片生成失败: 抛出 GenerationError
- 音频生成失败: 抛出 SynthesisError
- 无音频文本: 生成静音音频

## 5. 配置项

```python
class SceneRendererConfig:
    qiniu_api_key: str
    qiniu_endpoint: str = "https://openai.qiniu.com"
    image_model: str = "dall-e-3"
    image_size: str = "1024x1024"
    tts_encoding: str = "mp3"
    tts_speed_ratio: float = 1.0
    retry_attempts: int = 3
    timeout: int = 300
    narrator_voice_type: str = "qiniu_zh_female_tmjxxy"
    default_voice_type: str = "qiniu_zh_female_tmjxxy"
    silent_audio_duration: float = 3.0
```

## 6. 使用示例

```python
from agents.scene_renderer import SceneRenderer, SceneRendererConfig
from agents.storyboard.models import StoryboardResult

renderer = SceneRenderer(
    task_id="task-123",
    config=SceneRendererConfig(qiniu_api_key="your-api-key")
)

storyboard_result = StoryboardResult(...)
render_result = await renderer.render(storyboard_result)

print(f"Rendered {render_result.total_scenes} scenes")
print(f"Total duration: {render_result.total_duration}s")
```

## 7. 性能优化

### 7.1 串行处理

目前采用串行处理场景，确保API调用稳定。每个场景渲染完成后等待1秒再处理下一个。

### 7.2 存储优化

- 使用 TaskStorageManager 管理文件存储
- 图片和音频分别存储在 images/ 和 audios/ 子目录
- 文件名使用 UUID 避免冲突

## 8. 依赖关系

- **上游**: StoryboardAgent (提供 StoryboardResult)
- **下游**: SceneComposer (接收 RenderResult)
- **外部服务**: 七牛云 Image Generation API, 七牛云 TTS API
