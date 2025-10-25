from pydantic import BaseModel, Field
from typing import Optional


class VoiceSynthesizerConfig(BaseModel):
    # Qiniu API configuration
    qiniu_api_key: str = Field(default="", description="Qiniu API Key")
    qiniu_endpoint: str = Field(default="https://openai.qiniu.com", description="Qiniu AI API endpoint")
    
    # Audio generation parameters
    voice_type: str = Field(default="qiniu_zh_female_wwxkjx", description="Voice type for synthesis")
    encoding: str = Field(default="mp3", description="Audio encoding format")
    speed_ratio: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed ratio")
    
    # Storage configuration
    audio_format: str = Field(default="mp3", description="Output audio format")
    enable_post_processing: bool = Field(default=False, description="Enable audio post-processing")
    fade_duration: int = Field(default=100, ge=0, description="Fade in/out duration in milliseconds")
    max_text_length: int = Field(default=4096, description="Maximum text length for TTS")
    task_storage_base_path: str = Field(
        default="./data/tasks",
        description="Base path for task storage"
    )