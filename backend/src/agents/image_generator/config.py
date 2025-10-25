from pydantic import BaseModel, Field
from typing import Literal, Optional


class ImageGeneratorConfig(BaseModel):
    # Qiniu API configuration
    qiniu_api_key: str = Field(default="", description="Qiniu API Key")
    qiniu_endpoint: str = Field(default="https://openai.qiniu.com", description="Qiniu AI API endpoint")
    
    # Image generation parameters
    model: str = Field(
        default="gemini-2.5-flash-image",
        description="Image generation model (e.g., qwen-image-plus, wanx-v3)"
    )
    size: str = Field(default="1024x1024", description="Image size (e.g., 1024x1024, 1328x1328)")
    batch_size: int = Field(default=5, description="Batch size for concurrent generation", ge=1)
    retry_attempts: int = Field(default=3, description="Number of retry attempts", ge=1)
    timeout: int = Field(default=60, description="Timeout in seconds", ge=10)
    
    # Storage configuration
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
    
    # Image generation mode
    generation_mode: Literal["text2image", "image2image"] = Field(
        default="text2image",
        description="Generation mode: text2image or image2image"
    )