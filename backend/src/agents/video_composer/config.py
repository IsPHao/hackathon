from pydantic import BaseModel, Field
from typing import Literal


class VideoComposerConfig(BaseModel):
    fps: int = Field(default=24, description="Video frame rate", ge=1, le=60)
    resolution: str = Field(default="1920x1080", description="Video resolution")
    codec: str = Field(default="libx264", description="Video codec")
    audio_codec: str = Field(default="aac", description="Audio codec")
    preset: Literal["ultrafast", "fast", "medium", "slow"] = Field(
        default="medium",
        description="Encoding preset"
    )
    bitrate: str = Field(default="5000k", description="Video bitrate")
    audio_bitrate: str = Field(default="128k", description="Audio bitrate")
    temp_dir: str = Field(default="/tmp/video_composition", description="Temporary directory")
    storage_type: Literal["local", "oss"] = Field(
        default="local",
        description="Storage type: local or oss"
    )
    local_storage_path: str = Field(
        default="./data/videos",
        description="Local storage path"
    )
    oss_bucket: str = Field(default="", description="OSS bucket name")
    oss_endpoint: str = Field(default="", description="OSS endpoint")
    oss_access_key: str = Field(default="", description="OSS access key")
    oss_secret_key: str = Field(default="", description="OSS secret key")
    timeout: int = Field(default=300, description="Timeout in seconds", ge=30)
