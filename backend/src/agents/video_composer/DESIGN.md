# Video Composer Agent 设计文档

## 1. Agent概述

### 1.1 职责
视频合成Agent负责将生成的图片、音频和字幕合成为最终的视频文件。

### 1.2 核心功能
- 图片序列合成
- 音频轨道合成
- 字幕添加
- 转场效果
- 视频导出和上传

## 2. 技术选型

- **核心工具**: FFmpeg + moviepy
- **格式**: MP4 (H.264 + AAC)
- **分辨率**: 1920x1080
- **帧率**: 24fps

## 3. 核心实现

```python
from moviepy.editor import *
import subprocess

class VideoComposerAgent:
    
    def __init__(self, storage_service):
        self.storage = storage_service
        self.temp_dir = "/tmp/video_composition"
    
    async def compose(
        self,
        images: List[str],
        audios: List[str],
        storyboard: Dict
    ) -> Dict:
        """合成视频"""
        # 1. 下载素材
        local_images = await self._download_images(images)
        local_audios = await self._download_audios(audios)
        
        # 2. 创建视频片段
        clips = []
        for i, scene in enumerate(storyboard["scenes"]):
            clip = await self._create_scene_clip(
                local_images[i],
                local_audios[i],
                scene
            )
            clips.append(clip)
        
        # 3. 拼接视频
        final_video = concatenate_videoclips(
            clips,
            method="compose"
        )
        
        # 4. 导出
        output_path = f"{self.temp_dir}/output.mp4"
        final_video.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            bitrate='5000k'
        )
        
        # 5. 上传
        video_url = await self._upload_video(output_path)
        thumbnail_url = await self._generate_thumbnail(output_path)
        
        return {
            "url": video_url,
            "thumbnail_url": thumbnail_url,
            "duration": final_video.duration,
            "file_size": os.path.getsize(output_path)
        }
    
    async def _create_scene_clip(
        self,
        image_path: str,
        audio_path: str,
        scene: Dict
    ) -> VideoClip:
        """创建单个场景片段"""
        # 1. 图片剪辑
        img_clip = ImageClip(image_path).set_duration(scene["duration"])
        
        # 2. 添加字幕
        if scene.get("dialogue"):
            txt_clip = TextClip(
                scene["dialogue"],
                fontsize=32,
                color='white',
                font='Arial',
                stroke_color='black',
                stroke_width=2,
                method='caption',
                size=(img_clip.w * 0.8, None)
            ).set_position(('center', 0.85), relative=True).set_duration(scene["duration"])
            
            img_clip = CompositeVideoClip([img_clip, txt_clip])
        
        # 3. 添加音频
        if audio_path:
            audio = AudioFileClip(audio_path)
            img_clip = img_clip.set_audio(audio)
        
        # 4. 添加转场
        if scene.get("transition") == "fade":
            img_clip = img_clip.crossfadein(0.5)
        
        return img_clip
```

## 4. FFmpeg优化

```python
async def _compose_with_ffmpeg(
    self,
    images: List[str],
    audios: List[str]
) -> str:
    """使用FFmpeg直接合成（更快）"""
    # 创建输入文件列表
    concat_file = self._create_concat_file(images, audios)
    
    # FFmpeg命令
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        'output.mp4'
    ]
    
    # 执行
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    await process.wait()
    
    return 'output.mp4'
```

## 5. 性能优化

- 使用硬件加速（GPU编码）
- 并行处理多个场景
- 预加载素材到内存
- 使用高效编码参数

## 6. 性能指标

- 合成速度: 1x实时（30场景/10分钟）
- 文件大小: ~50MB/5分钟视频
- 成功率: >98%
- 质量评分: >90%
