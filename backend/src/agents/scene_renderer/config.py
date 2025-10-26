from typing import Optional
from pydantic import BaseModel, Field


class SceneRendererConfig(BaseModel):
    qiniu_api_key: str = Field(default="", description="七牛云API密钥")
    qiniu_endpoint: str = Field(
        default="https://openai.qiniu.com",
        description="七牛云API端点"
    )
    
    image_model: str = Field(default="stable-diffusion-v1-5", description="图像生成模型")
    image_size: str = Field(default="512x512", description="图像尺寸")
    
    tts_encoding: str = Field(default="mp3", description="音频编码格式")
    tts_speed_ratio: float = Field(default=1.0, description="语音速度比率")
    
    task_storage_base_path: str = Field(
        default="./data/tasks",
        description="任务存储基础路径"
    )
    
    timeout: int = Field(default=60, description="API请求超时时间（秒）")
    retry_attempts: int = Field(default=3, description="失败重试次数")
    
    default_voice_type: str = Field(
        default="qiniu_zh_female_wwxkjx",
        description="默认语音类型"
    )
    narrator_voice_type: str = Field(
        default="qiniu_zh_male_tyygjs",
        description="旁白语音类型"
    )
    
    silent_audio_duration: float = Field(
        default=3.0,
        description="空白音频默认时长（秒）"
    )
