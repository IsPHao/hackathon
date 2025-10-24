import pytest
from pydantic import ValidationError

from backend.src.agents.novel_parser import NovelParserConfig


def test_default_config():
    config = NovelParserConfig()
    
    assert config.model == "gpt-4o-mini"
    assert config.max_characters == 10
    assert config.max_scenes == 30
    assert config.temperature == 0.3
    assert config.enable_character_enhancement is True
    assert config.enable_caching is True
    assert config.cache_ttl == 7 * 24 * 3600
    assert config.min_text_length == 100
    assert config.max_text_length == 50000


def test_custom_config():
    config = NovelParserConfig(
        model="gpt-4o",
        max_characters=20,
        max_scenes=50,
        temperature=0.7,
        enable_character_enhancement=False,
        enable_caching=False,
        cache_ttl=3600,
        min_text_length=200,
        max_text_length=100000
    )
    
    assert config.model == "gpt-4o"
    assert config.max_characters == 20
    assert config.max_scenes == 50
    assert config.temperature == 0.7
    assert config.enable_character_enhancement is False
    assert config.enable_caching is False
    assert config.cache_ttl == 3600
    assert config.min_text_length == 200
    assert config.max_text_length == 100000


def test_config_partial_override():
    config = NovelParserConfig(
        model="gpt-4o",
        max_characters=15
    )
    
    assert config.model == "gpt-4o"
    assert config.max_characters == 15
    assert config.max_scenes == 30
    assert config.temperature == 0.3
