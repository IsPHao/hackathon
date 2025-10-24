from pydantic_settings import BaseSettings
from pydantic import Field


class CoreSettings(BaseSettings):
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_backoff_base: int = Field(default=2, description="Backoff base for exponential retry")
    task_timeout: int = Field(default=3600, description="Task timeout in seconds")
    cleanup_interval: int = Field(default=3600, description="Cleanup interval in seconds")
    
    class Config:
        env_prefix = "CORE_"
