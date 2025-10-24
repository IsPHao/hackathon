from pydantic_settings import BaseSettings
from pydantic import Field


class CoreSettings(BaseSettings):
    """
    核心模块配置
    
    配置项可通过环境变量设置,前缀为CORE_,例如:
    - CORE_MAX_RETRIES=5
    - CORE_RETRY_BACKOFF_BASE=3
    - CORE_TASK_TIMEOUT=7200
    """
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_backoff_base: int = Field(default=2, description="Backoff base for exponential retry")
    task_timeout: int = Field(default=3600, description="Task timeout in seconds")
    cleanup_interval: int = Field(default=3600, description="Cleanup interval in seconds")
    
    class Config:
        env_prefix = "CORE_"
