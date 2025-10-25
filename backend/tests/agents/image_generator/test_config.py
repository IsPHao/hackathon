import pytest
from pydantic import ValidationError as PydanticValidationError
from src.agents.image_generator.config import ImageGeneratorConfig


def test_config_defaults():
    """Test default configuration values"""
    config = ImageGeneratorConfig()
    
    # Qiniu API defaults
    assert config.qiniu_api_key == ""
    assert config.qiniu_endpoint == "https://openai.qiniu.com"
    
    # Image generation defaults
    assert config.model == "qwen-image-plus"
    assert config.size == "1024x1024"
    assert config.batch_size == 5
    assert config.retry_attempts == 3
    assert config.timeout == 60
    
    # Storage defaults
    assert config.storage_type == "local"
    assert config.local_storage_path == "./data/images"
    assert config.task_storage_base_path == "./data/tasks"
    
    # Generation mode
    assert config.generation_mode == "text2image"


def test_config_custom_values():
    """Test custom configuration values"""
    config = ImageGeneratorConfig(
        qiniu_api_key="test_api_key",
        model="wanx-v3",
        size="1344x1344",
        batch_size=10,
        retry_attempts=5,
        timeout=120,
        generation_mode="image2image"
    )
    
    assert config.qiniu_api_key == "test_api_key"
    assert config.model == "wanx-v3"
    assert config.size == "1344x1344"
    assert config.batch_size == 10
    assert config.retry_attempts == 5
    assert config.timeout == 120
    assert config.generation_mode == "image2image"


def test_config_validation():
    """Test configuration validation"""
    # Test batch_size minimum value
    with pytest.raises(PydanticValidationError):
        ImageGeneratorConfig(batch_size=0)
    
    # Test retry_attempts minimum value
    with pytest.raises(PydanticValidationError):
        ImageGeneratorConfig(retry_attempts=0)
    
    # Test timeout minimum value
    with pytest.raises(PydanticValidationError):
        ImageGeneratorConfig(timeout=5)
    
    # Test generation_mode valid values
    config = ImageGeneratorConfig(generation_mode="text2image")
    assert config.generation_mode == "text2image"
    
    config = ImageGeneratorConfig(generation_mode="image2image")
    assert config.generation_mode == "image2image"