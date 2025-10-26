# SceneComposer 模块设计文档

## 1. 模块概述

SceneComposer 负责将渲染完成的场景合成为最终的视频文件。

### 1.1 职责
- 接收 RenderResult 作为输入
- 将每个场景的图片和音频合成为视频片段
- 将同一章节的视频片段拼接成章节视频
- 将所有章节视频拼接成最终视频
- 返回视频信息（路径、时长、文件大小等）

### 1.2 输入输出

**输入**: `RenderResult`
- 包含所有章节的渲染结果
- 每个场景包含图片路径和音频路径

**输出**: `Dict[str, Any]`
- video_path: 最终视频路径
- duration: 视频总时长
- file_size: 文件大小
- total_scenes: 场景总数
- total_chapters: 章节总数

## 2. 核心功能

### 2.1 场景合成

将单个场景的图片和音频合成为视频片段。

```python
async def _compose_scene(self, scene: RenderedScene) -> str:
    output_path = self.temp_dir / f"scene_{scene.scene_id}_{uuid}.mp4"
    
    cmd = self._build_scene_ffmpeg_cmd(
        scene.image_path,
        scene.audio_path,
        str(output_path),
        duration
    )
    
    # 执行 FFmpeg 命令
    process = await asyncio.create_subprocess_exec(*cmd, ...)
    
    return str(output_path)
```

**FFmpeg 命令**:
```bash
ffmpeg -y \
  -loop 1 -i image.png \
  -i audio.mp3 \
  -c:v libx264 -preset fast -tune stillimage \
  -c:a aac -b:a 192k \
  -pix_fmt yuv420p \
  -shortest -t duration \
  output.mp4
```

### 2.2 章节视频拼接

将同一章节的所有场景视频拼接成章节视频。

```python
async def _compose_chapter(self, chapter: RenderedChapter) -> str:
    scene_videos = []
    for scene in chapter.scenes:
        scene_video_path = await self._compose_scene(scene)
        scene_videos.append(scene_video_path)
    
    if len(scene_videos) == 1:
        return scene_videos[0]
    
    chapter_video_path = await self._concatenate_videos(
        scene_videos,
        f"chapter_{chapter.chapter_id}"
    )
    
    return chapter_video_path
```

### 2.3 最终视频拼接

将所有章节视频拼接成最终视频。

```python
async def compose(self, render_result: RenderResult) -> Dict[str, Any]:
    chapter_videos = []
    for chapter in render_result.chapters:
        chapter_video_path = await self._compose_chapter(chapter)
        chapter_videos.append(chapter_video_path)
    
    if len(chapter_videos) == 1:
        final_video_path = chapter_videos[0]
    else:
        final_video_path = await self._concatenate_videos(
            chapter_videos,
            "final_video"
        )
    
    return {
        "video_path": final_video_path,
        "duration": await self._get_video_duration(final_video_path),
        "file_size": os.path.getsize(final_video_path),
        "total_scenes": render_result.total_scenes,
        "total_chapters": len(render_result.chapters)
    }
```

### 2.4 视频拼接

使用 FFmpeg concat 功能拼接多个视频。

```python
async def _concatenate_videos(
    self,
    video_paths: List[str],
    output_name: str
) -> str:
    # 创建拼接列表文件
    concat_file = self.temp_dir / f"{output_name}_concat_{uuid}.txt"
    with open(concat_file, "w") as f:
        for video_path in video_paths:
            f.write(f"file '{os.path.abspath(video_path)}'\n")
    
    # 执行拼接
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path)
    ]
    
    process = await asyncio.create_subprocess_exec(*cmd, ...)
    
    return str(output_path)
```

## 3. 数据模型

### 3.1 输入模型

```python
class RenderResult:
    chapters: List[RenderedChapter]
    total_duration: float
    total_scenes: int
    output_directory: str

class RenderedChapter:
    chapter_id: int
    title: str
    scenes: List[RenderedScene]
    total_duration: float

class RenderedScene:
    scene_id: str
    chapter_id: int
    image_path: str
    audio_path: str
    duration: float
    audio_duration: float
    metadata: Dict[str, Any]
```

### 3.2 输出

```python
{
    "video_path": "/path/to/final_video.mp4",
    "duration": 120.5,
    "file_size": 10485760,
    "total_scenes": 15,
    "total_chapters": 3
}
```

## 4. 错误处理

### 4.1 输入验证

```python
def _validate_input(self, render_result: RenderResult):
    if not render_result.chapters:
        raise ValidationError("RenderResult must have at least one chapter")
    
    for chapter in render_result.chapters:
        if not chapter.scenes:
            raise ValidationError(f"Chapter {chapter.chapter_id} must have at least one scene")
        
        for scene in chapter.scenes:
            if not scene.image_path:
                raise ValidationError(f"Scene {scene.scene_id} must have an image_path")
```

### 4.2 超时处理

每个 FFmpeg 操作都有超时机制，默认 300 秒。

```python
try:
    stdout, stderr = await asyncio.wait_for(
        process.communicate(),
        timeout=self.config.timeout,
    )
except asyncio.TimeoutError:
    if process:
        process.kill()
        await process.wait()
    raise CompositionError("FFmpeg operation timed out")
```

### 4.3 临时文件清理

场景视频在章节视频合成后会被清理，减少磁盘占用。

```python
async def _compose_chapter(self, chapter: RenderedChapter) -> str:
    scene_videos = []
    try:
        # 合成场景视频
        for scene in chapter.scenes:
            scene_video_path = await self._compose_scene(scene)
            scene_videos.append(scene_video_path)
        
        # 拼接成章节视频
        chapter_video_path = await self._concatenate_videos(...)
        return chapter_video_path
    finally:
        # 清理场景视频
        if len(scene_videos) > 1:
            for scene_video in scene_videos:
                if os.path.exists(scene_video):
                    os.unlink(scene_video)
```

## 5. 配置项

```python
class SceneComposerConfig:
    codec: str = "libx264"
    preset: str = "fast"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    timeout: int = 300
    uuid_suffix_length: int = 8
    task_storage_base_path: str = "./data/tasks"
```

## 6. 使用示例

```python
from agents.scene_composer import SceneComposer, SceneComposerConfig
from agents.scene_renderer.models import RenderResult

composer = SceneComposer(
    task_id="task-123",
    config=SceneComposerConfig()
)

render_result = RenderResult(...)
video_result = await composer.execute(render_result)

print(f"Video created: {video_result['video_path']}")
print(f"Duration: {video_result['duration']}s")
print(f"Size: {video_result['file_size']} bytes")
```

## 7. 性能优化

### 7.1 FFmpeg 参数优化

- **编码器**: libx264 (H.264)
- **预设**: fast (平衡速度和质量)
- **tune**: stillimage (优化静态图片编码)
- **音频编码**: AAC, 192kbps

### 7.2 并发控制

目前采用串行处理，确保内存和磁盘占用可控。未来可以考虑并发处理不同章节。

## 8. 健康检查

```python
async def health_check(self) -> bool:
    # 检查 FFmpeg 是否可用
    ffmpeg_result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
    if ffmpeg_result.returncode != 0:
        return False
    
    # 检查 FFprobe 是否可用
    ffprobe_result = subprocess.run(['ffprobe', '-version'], capture_output=True)
    if ffprobe_result.returncode != 0:
        return False
    
    return True
```

## 9. 依赖关系

- **上游**: SceneRenderer (提供 RenderResult)
- **外部工具**: FFmpeg, FFprobe
- **文件系统**: TaskStorageManager (存储临时和最终文件)
