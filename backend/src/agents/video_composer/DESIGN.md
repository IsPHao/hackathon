# Video Composer Agent 设计文档

## 1. Agent概述

### 1.1 职责
视频合成Agent负责将视频片段和音频片段合成为最终的MP4视频文件。

### 1.2 核心功能
- 视频和音频片段合并
- 多个片段拼接
- 输入验证和文件检查
- 视频时长和大小计算

### 1.3 重要变更（重构后）
- **不再继承 BaseAgent**：VideoComposerAgent 现在是独立的类
- **新的输入格式**：使用 VideoSegment 和 AudioSegment 对象替代 URL 列表
- **本地文件优先**：所有输入必须是本地文件路径，在处理前会检查文件是否存在
- **简化的输出**：输出为本地 MP4 文件，不再包含上传和缩略图生成

## 2. 技术选型

- **核心工具**: FFmpeg
- **格式**: MP4 (H.264 + AAC)
- **音频编解码器**: AAC (默认 128k 比特率)

## 3. 数据模型

### 3.1 VideoSegment
视频片段信息模型：
```python
class VideoSegment(BaseModel):
    path: str              # 视频文件本地路径（必需）
    duration: float        # 视频时长(秒)（必需，必须 > 0）
    width: Optional[int]   # 视频宽度（可选）
    height: Optional[int]  # 视频高度（可选）
    format: Optional[str]  # 视频格式（可选）
```

### 3.2 AudioSegment
音频片段信息模型：
```python
class AudioSegment(BaseModel):
    path: str              # 音频文件本地路径（必需）
    duration: float        # 音频时长(秒)（必需，必须 > 0）
    format: Optional[str]  # 音频格式（可选）
    bitrate: Optional[str] # 音频比特率（可选）
```

## 4. 核心实现

### 4.1 基本使用

```python
from backend.src.agents.video_composer import (
    VideoComposerAgent,
    VideoSegment,
    AudioSegment
)

# 创建 Agent 实例
agent = VideoComposerAgent(
    task_id="task_123",
    config=VideoComposerConfig()
)

# 准备视频和音频片段
video_segments = [
    VideoSegment(path="/path/to/video1.mp4", duration=5.0),
    VideoSegment(path="/path/to/video2.mp4", duration=3.0),
]

audio_segments = [
    AudioSegment(path="/path/to/audio1.mp3", duration=5.0),
    AudioSegment(path="/path/to/audio2.mp3", duration=3.0),
]

# 合成视频
result = await agent.compose_video(
    video_segments=video_segments,
    audio_segments=audio_segments,
    output_path="/path/to/output.mp4"  # 可选
)

print(f"输出路径: {result['output_path']}")
print(f"总时长: {result['duration']} 秒")
print(f"文件大小: {result['file_size']} 字节")
```

### 4.2 处理流程

1. **输入验证**
   - 检查 video_segments 和 audio_segments 是否为列表
   - 检查列表是否为空
   - 检查每个片段是否包含必需字段
   - 检查时长是否大于 0
   - 检查视频和音频片段数量是否相同

2. **文件存在性检查**
   - 检查所有视频文件路径是否存在
   - 检查所有音频文件路径是否存在
   - 检查路径是否指向文件（而非目录）

3. **合并视频和音频**
   - 对每一对视频-音频片段进行合并
   - 使用 FFmpeg 将音频轨道添加到视频中
   - 生成临时片段文件

4. **拼接视频片段**
   - 创建 FFmpeg concat 列表文件
   - 使用 FFmpeg concat demuxer 拼接所有片段
   - 生成最终输出视频

5. **计算元数据**
   - 使用 FFprobe 获取视频时长
   - 获取输出文件大小

6. **返回结果**
   - 返回包含输出路径、时长和文件大小的字典

## 5. FFmpeg 命令详解

### 5.1 合并视频和音频
```bash
ffmpeg -y \
  -i video.mp4 \
  -i audio.mp3 \
  -c:v copy \           # 复制视频流，不重新编码
  -c:a aac \            # 音频编码为 AAC
  -b:a 128k \           # 音频比特率 128k
  -shortest \           # 以较短的流为准
  output.mp4
```

### 5.2 拼接视频片段
```bash
# 1. 创建 concat_list.txt
# file '/path/to/clip_0.mp4'
# file '/path/to/clip_1.mp4'

# 2. 拼接
ffmpeg -y \
  -f concat \
  -safe 0 \
  -i concat_list.txt \
  -c copy \             # 直接复制流，不重新编码
  final_output.mp4
```

### 5.3 获取视频时长
```bash
ffprobe -v quiet \
  -print_format json \
  -show_format \
  video.mp4
```

## 6. 错误处理

### 6.1 验证错误 (ValidationError)
- 输入参数类型错误
- 片段列表为空
- 视频和音频片段数量不匹配
- 文件不存在或路径无效
- 时长小于等于 0

### 6.2 合成错误 (CompositionError)
- FFmpeg 执行失败
- 超时错误
- 文件读写错误

## 7. 配置参数

通过 `VideoComposerConfig` 配置：

```python
VideoComposerConfig(
    fps=24,                           # 视频帧率（已废弃，保留以兼容）
    resolution="1920x1080",           # 视频分辨率（已废弃，保留以兼容）
    codec="libx264",                  # 视频编解码器（已废弃，保留以兼容）
    audio_codec="aac",                # 音频编解码器
    preset="medium",                  # 编码预设（已废弃，保留以兼容）
    bitrate="5000k",                  # 视频比特率（已废弃，保留以兼容）
    audio_bitrate="128k",             # 音频比特率
    task_storage_base_path="./data/tasks",  # 任务存储基础路径
    storage_type="local",             # 存储类型
    local_storage_path="./data/videos",     # 本地存储路径
    timeout=300,                      # 超时时间（秒）
)
```

**注意**：由于重构后直接使用输入的视频片段，某些配置参数（如 fps、resolution、codec 等）不再用于视频编码，仅保留以保持配置兼容性。

## 8. 性能优化建议

- **使用 `-c copy`**：直接复制视频流，避免重新编码，大幅提升速度
- **预处理片段**：确保所有输入视频片段使用相同的编解码器和参数
- **并行处理**：可以并行合并多对视频-音频片段（当前实现为串行）
- **调整超时时间**：根据视频长度和数量调整 timeout 参数

## 9. 健康检查

Agent 提供健康检查方法：

```python
is_healthy = await agent.health_check()
```

检查项目：
- FFmpeg 是否可用
- FFprobe 是否可用

## 10. 临时文件清理

```python
# 使用完毕后清理临时文件
agent.cleanup_temp_files()
```

清理内容：
- 合并后的片段文件
- concat 列表文件
- 其他临时文件

## 11. 使用示例

### 示例 1: 基本使用
```python
agent = VideoComposerAgent(task_id="demo")

videos = [
    VideoSegment(path="scene1.mp4", duration=5.0),
    VideoSegment(path="scene2.mp4", duration=3.0),
]

audios = [
    AudioSegment(path="voice1.mp3", duration=5.0),
    AudioSegment(path="voice2.mp3", duration=3.0),
]

result = await agent.compose_video(videos, audios)
print(f"输出: {result['output_path']}")
```

### 示例 2: 带完整元数据
```python
videos = [
    VideoSegment(
        path="scene1.mp4",
        duration=5.0,
        width=1920,
        height=1080,
        format="mp4"
    ),
]

audios = [
    AudioSegment(
        path="voice1.mp3",
        duration=5.0,
        format="mp3",
        bitrate="192k"
    ),
]

result = await agent.compose_video(
    video_segments=videos,
    audio_segments=audios,
    output_path="/custom/output/path.mp4"
)
```

### 示例 3: 错误处理
```python
try:
    result = await agent.compose_video(videos, audios)
except ValidationError as e:
    print(f"输入验证失败: {e}")
except CompositionError as e:
    print(f"视频合成失败: {e}")
finally:
    agent.cleanup_temp_files()
```

## 12. 迁移指南

### 从旧版本迁移

**旧版本 API**:
```python
await agent.execute(
    images=["image1.png", "image2.png"],
    audios=["audio1.mp3", "audio2.mp3"],
    storyboard={"scenes": [{"duration": 3.0}, {"duration": 5.0}]}
)
```

**新版本 API**:
```python
await agent.compose_video(
    video_segments=[
        VideoSegment(path="video1.mp4", duration=3.0),
        VideoSegment(path="video2.mp4", duration=5.0)
    ],
    audio_segments=[
        AudioSegment(path="audio1.mp3", duration=3.0),
        AudioSegment(path="audio2.mp3", duration=5.0)
    ]
)
```

**主要变更**:
1. 不再使用 `execute()` 方法，改用 `compose_video()`
2. 不再接受图片输入，必须是视频片段
3. 不再接受 storyboard，时长信息在片段对象中
4. 所有资源必须是本地文件，不再支持 URL 下载
5. 输出为本地文件，不再自动上传或生成缩略图
