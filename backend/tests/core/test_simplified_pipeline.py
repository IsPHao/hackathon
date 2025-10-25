import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

# Mock the missing modules
import sys
from unittest.mock import MagicMock

# Mock the missing modules in backend.src.core
sys.modules['backend.src.core.task_manager'] = MagicMock()
sys.modules['backend.src.core.progress_tracker'] = MagicMock()
sys.modules['backend.src.core.error_handler'] = MagicMock()
sys.modules['backend.src.core.context'] = MagicMock()
sys.modules['backend.src.core.interfaces'] = MagicMock()
sys.modules['backend.src.core.config'] = MagicMock()
sys.modules['backend.src.core.llm_factory'] = MagicMock()
sys.modules['backend.src.core.cache'] = MagicMock()

from backend.src.core.pipeline import AnimePipeline


@pytest.fixture
def mock_llm():
    return Mock()


@pytest.fixture
def mock_agents(mock_llm):
    with patch('backend.src.core.pipeline.ChatOpenAI', return_value=mock_llm):
        with patch('backend.src.core.pipeline.NovelParserAgent') as mock_novel_parser, \
             patch('backend.src.core.pipeline.StoryboardAgent') as mock_storyboard, \
             patch('backend.src.core.pipeline.CharacterConsistencyAgent') as mock_character_consistency, \
             patch('backend.src.core.pipeline.ImageGeneratorAgent') as mock_image_generator, \
             patch('backend.src.core.pipeline.VoiceSynthesizerAgent') as mock_voice_synthesizer, \
             patch('backend.src.core.pipeline.VideoComposerAgent') as mock_video_composer:
            
            # Setup mock return values
            mock_novel_parser.return_value.execute = AsyncMock(return_value={
                "characters": [{"name": "Alice"}],
                "scenes": [{"scene_id": 1, "image_prompt": "A beautiful garden"}],
                "plot_points": []
            })
            
            mock_storyboard.return_value.execute = AsyncMock(return_value={
                "scenes": [{"scene_id": 1, "image_prompt": "A beautiful garden", "duration": 5.0}]
            })
            
            mock_character_consistency.return_value.execute = AsyncMock(return_value={
                "Alice": Mock()
            })
            
            mock_image_generator.return_value.execute = AsyncMock(return_value="/path/to/image1.png")
            mock_voice_synthesizer.return_value.execute = AsyncMock(return_value="/path/to/audio1.mp3")
            
            mock_video_composer.return_value.execute = AsyncMock(return_value={
                "url": "/path/to/final_video.mp4",
                "thumbnail_url": "/path/to/thumbnail.jpg",
                "duration": 120.0,
                "file_size": 1024000
            })
            
            yield {
                "novel_parser": mock_novel_parser,
                "storyboard": mock_storyboard,
                "character_consistency": mock_character_consistency,
                "image_generator": mock_image_generator,
                "voice_synthesizer": mock_voice_synthesizer,
                "video_composer": mock_video_composer
            }


@pytest.mark.asyncio
async def test_pipeline_initialization():
    """Test that the pipeline initializes all agents correctly"""
    with patch('backend.src.core.pipeline.ChatOpenAI') as mock_llm:
        pipeline = AnimePipeline()
        
        # Check that all agents are initialized
        assert pipeline.novel_parser is not None
        assert pipeline.storyboard is not None
        assert pipeline.character_consistency is not None
        assert pipeline.image_generator is not None
        assert pipeline.voice_synthesizer is not None
        assert pipeline.video_composer is not None


@pytest.mark.asyncio
async def test_pipeline_execute_success(mock_agents):
    """Test successful execution of the pipeline"""
    pipeline = AnimePipeline()
    
    novel_text = "Test novel text about a beautiful garden"
    
    result = await pipeline.execute(novel_text)
    
    # Verify the result
    assert "video_path" in result
    assert result["video_path"] == "/path/to/final_video.mp4"
    assert result["scenes_count"] == 1
    
    # Verify that all agents were called
    mock_agents["novel_parser"].return_value.execute.assert_called_once_with(novel_text)
    mock_agents["storyboard"].return_value.execute.assert_called_once()
    mock_agents["character_consistency"].return_value.execute.assert_called_once()
    mock_agents["image_generator"].return_value.execute.assert_called_once()
    mock_agents["voice_synthesizer"].return_value.execute.assert_called_once()
    mock_agents["video_composer"].return_value.execute.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_execute_with_multiple_scenes(mock_agents):
    """Test pipeline execution with multiple scenes"""
    # Update the novel parser mock to return multiple scenes
    mock_agents["novel_parser"].return_value.execute.return_value = {
        "characters": [{"name": "Alice"}, {"name": "Bob"}],
        "scenes": [
            {"scene_id": 1, "image_prompt": "A beautiful garden"},
            {"scene_id": 2, "image_prompt": "A cozy kitchen"}
        ],
        "plot_points": []
    }
    
    # Update the storyboard mock to return multiple scenes
    mock_agents["storyboard"].return_value.execute.return_value = {
        "scenes": [
            {"scene_id": 1, "image_prompt": "A beautiful garden", "duration": 5.0},
            {"scene_id": 2, "image_prompt": "A cozy kitchen", "duration": 4.0}
        ]
    }
    
    # Update image and voice generator mocks to handle multiple calls
    mock_agents["image_generator"].return_value.execute = AsyncMock(side_effect=[
        "/path/to/image1.png",
        "/path/to/image2.png"
    ])
    
    mock_agents["voice_synthesizer"].return_value.execute = AsyncMock(side_effect=[
        "/path/to/audio1.mp3",
        "/path/to/audio2.mp3"
    ])
    
    pipeline = AnimePipeline()
    novel_text = "Test novel with multiple scenes"
    
    result = await pipeline.execute(novel_text)
    
    # Verify the result
    assert result["scenes_count"] == 2
    assert result["video_path"] == "/path/to/final_video.mp4"
    
    # Verify call counts
    assert mock_agents["image_generator"].return_value.execute.call_count == 2
    assert mock_agents["voice_synthesizer"].return_value.execute.call_count == 2