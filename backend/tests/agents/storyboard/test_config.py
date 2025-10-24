import pytest
from src.agents.storyboard import StoryboardConfig


def test_default_config():
    config = StoryboardConfig()
    
    assert config.max_scenes == 30
    assert config.min_scene_duration == 3.0
    assert config.max_scene_duration == 10.0
    assert config.dialogue_chars_per_second == 3.0
    assert config.action_duration == 1.5
    assert config.temperature == 0.7


def test_custom_config():
    config = StoryboardConfig(
        max_scenes=20,
        min_scene_duration=2.0,
        max_scene_duration=8.0,
        temperature=0.5,
    )
    
    assert config.max_scenes == 20
    assert config.min_scene_duration == 2.0
    assert config.max_scene_duration == 8.0
    assert config.temperature == 0.5
