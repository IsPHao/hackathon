import pytest
from src.agents.image_generator import ImageGeneratorConfig


def test_config_defaults():
    config = ImageGeneratorConfig()
    
    assert config.model == "dall-e-3"
    assert config.size == "1024x1024"
    assert config.quality == "standard"
    assert config.n == 1
    assert config.batch_size == 5
    assert config.retry_attempts == 3
    assert config.timeout == 60
    assert config.storage_type == "local"


def test_config_custom_values():
    config = ImageGeneratorConfig(
        model="dall-e-2",
        size="512x512",
        quality="hd",
        batch_size=10,
        storage_type="oss",
        oss_bucket="my-bucket",
    )
    
    assert config.model == "dall-e-2"
    assert config.size == "512x512"
    assert config.quality == "hd"
    assert config.batch_size == 10
    assert config.storage_type == "oss"
    assert config.oss_bucket == "my-bucket"


def test_config_validation():
    with pytest.raises(ValueError):
        ImageGeneratorConfig(model="invalid-model")
    
    with pytest.raises(ValueError):
        ImageGeneratorConfig(quality="invalid-quality")
    
    with pytest.raises(ValueError):
        ImageGeneratorConfig(storage_type="invalid-storage")
