import pytest
from src.agents.character_consistency import CharacterConsistencyConfig


def test_default_config():
    config = CharacterConsistencyConfig()
    
    assert config.temperature == 0.7
    assert config.storage_base_path == "data/characters"
    assert config.enable_caching is True
    assert "anime style" in config.reference_image_prompt_suffix


def test_custom_config():
    config = CharacterConsistencyConfig(
        temperature=0.5,
        storage_base_path="custom/path",
        enable_caching=False,
    )
    
    assert config.temperature == 0.5
    assert config.storage_base_path == "custom/path"
    assert config.enable_caching is False
