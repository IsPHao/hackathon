import pytest
from pydantic import ValidationError

from src.agents.novel_parser import NovelParserConfig


def test_default_config():
    config = NovelParserConfig()
    
    assert config.max_characters == 10
    assert config.max_scenes == 30
    assert config.temperature == 0.3
    
    assert config.min_text_length == 100
    assert config.max_text_length == 50000


def test_custom_config():
    config = NovelParserConfig(
        max_characters=20,
        max_scenes=50,
        temperature=0.7,
        
        min_text_length=200,
        max_text_length=100000
    )
    
    assert config.max_characters == 20
    assert config.max_scenes == 50
    assert config.temperature == 0.7
    
    assert config.min_text_length == 200
    assert config.max_text_length == 100000


def test_config_partial_override():
    config = NovelParserConfig(
        max_characters=15
    )
    
    assert config.max_characters == 15
    assert config.max_scenes == 30
    assert config.temperature == 0.3