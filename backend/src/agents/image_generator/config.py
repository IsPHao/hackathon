from pydantic import BaseModel, Field
from typing import Literal, Optional


class ImageGeneratorConfig(BaseModel):
    model: Literal["dall-e-3", "dall-e-2"] = Field(
        default="dall-e-3",
        description="Image generation model"
    )
    size: str = Field(default="1024x1024", description="Image size")
    quality: Literal["standard", "hd"] = Field(
        default="standard",
        description="Image quality"
    )
    n: int = Field(default=1, description="Number of images to generate", ge=1, le=1)
    batch_size: int = Field(default=5, description="Batch size for concurrent generation", ge=1)
    retry_attempts: int = Field(default=3, description="Number of retry attempts", ge=1)
    timeout: int = Field(default=60, description="Timeout in seconds", ge=10)
    storage_type: Literal["local", "oss"] = Field(
        default="local",
        description="Storage type for generated images"
    )
    local_storage_path: str = Field(
        default="./data/images",
        description="Local storage path for images"
    )
    oss_bucket: str = Field(default="", description="OSS bucket name")
    oss_endpoint: str = Field(default="", description="OSS endpoint")
    oss_access_key: str = Field(default="", description="OSS access key")
    oss_secret_key: str = Field(default="", description="OSS secret key")
    task_storage_base_path: str = Field(
        default="./data/tasks",
        description="Base path for task storage"
    )