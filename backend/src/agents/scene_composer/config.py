from pydantic import BaseModel, Field


class SceneComposerConfig(BaseModel):
    timeout: int = Field(default=600, description="FFmpeg操作超时时间（秒）")
    codec: str = Field(default="libx264", description="视频编码器")
    preset: str = Field(default="medium", description="编码预设")
    audio_codec: str = Field(default="aac", description="音频编码器")
    audio_bitrate: str = Field(default="192k", description="音频比特率")
    task_storage_base_path: str = Field(
        default="./generated_files",
        description="任务存储基础路径"
    )
    uuid_suffix_length: int = Field(default=8, description="UUID后缀长度")
