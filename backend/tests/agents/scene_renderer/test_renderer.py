import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.agents.scene_renderer import (
    SceneRenderer,
    SceneRendererConfig,
    StoryboardResult,
    StoryboardChapter,
    StoryboardScene,
    CharacterRenderInfo,
    AudioInfo,
    ImageRenderInfo,
)


@pytest.fixture
def config():
    return SceneRendererConfig(
        qiniu_api_key="test_api_key",
        qiniu_endpoint="https://test.qiniu.com",
        task_storage_base_path="./test_data/tasks"
    )


@pytest.fixture
def renderer(config):
    return SceneRenderer(task_id="test_task_123", config=config)


@pytest.fixture
def sample_scene():
    return StoryboardScene(
        scene_id=1,
        chapter_id=1,
        location="教室",
        time="上午",
        atmosphere="轻松愉快",
        description="小明在教室里学习",
        characters=[
            CharacterRenderInfo(
                name="小明",
                gender="male",
                age=15,
                age_stage="青年",
                personality="开朗活泼"
            )
        ],
        audio=AudioInfo(
            type="dialogue",
            speaker="小明",
            text="你好，我是小明！",
            estimated_duration=2.0
        ),
        image=ImageRenderInfo(
            prompt="a young boy studying in classroom, anime style",
            style_tags=["anime", "school"]
        ),
        duration=3.0
    )


@pytest.fixture
def sample_storyboard(sample_scene):
    return StoryboardResult(
        chapters=[
            StoryboardChapter(
                chapter_id=1,
                title="第一章",
                summary="开始的故事",
                scenes=[sample_scene]
            )
        ],
        total_duration=3.0,
        total_scenes=1
    )


class TestSceneRenderer:
    
    def test_initialization(self, renderer, config):
        assert renderer.task_id == "test_task_123"
        assert renderer.config == config
        assert renderer.character_voice_cache == {}
    
    def test_match_voice_by_character_male_child(self, renderer):
        character = CharacterRenderInfo(
            name="小男孩",
            gender="male",
            age=8,
            age_stage="儿童"
        )
        voice_type = renderer._match_voice_by_character(character)
        assert "male" in voice_type or "child" in voice_type or voice_type in [
            "qiniu_zh_male_hlsnkk",
            "qiniu_zh_male_qslymb",
            "qiniu_zh_male_hllzmz",
            "qiniu_zh_male_etgsxe",
            "qiniu_zh_male_tcsnsf",
        ]
    
    def test_match_voice_by_character_female_adult(self, renderer):
        character = CharacterRenderInfo(
            name="女老师",
            gender="female",
            age=35,
            age_stage="成年"
        )
        voice_type = renderer._match_voice_by_character(character)
        assert "female" in voice_type
    
    def test_match_voice_by_character_unknown(self, renderer):
        character = CharacterRenderInfo(
            name="神秘人",
            gender="unknown",
            age_stage=""
        )
        voice_type = renderer._match_voice_by_character(character)
        assert voice_type == renderer.config.default_voice_type
    
    def test_build_image_prompt(self, renderer, sample_scene):
        prompt = renderer._build_image_prompt(sample_scene)
        assert "anime" in prompt
        assert "school" in prompt
        assert "high quality" in prompt
    
    def test_build_image_prompt_no_prompt(self, renderer, sample_scene):
        sample_scene.image.prompt = ""
        prompt = renderer._build_image_prompt(sample_scene)
        assert sample_scene.description in prompt
    
    def test_select_voice_type_narration(self, renderer, sample_scene):
        sample_scene.audio.type = "narration"
        voice_type = renderer._select_voice_type(sample_scene)
        assert voice_type == renderer.config.narrator_voice_type
    
    def test_select_voice_type_dialogue_with_character(self, renderer, sample_scene):
        voice_type = renderer._select_voice_type(sample_scene)
        assert voice_type is not None
        assert "qiniu" in voice_type
    
    def test_prepare_character_voices(self, renderer, sample_storyboard):
        renderer._prepare_character_voices(sample_storyboard)
        assert "小明" in renderer.character_voice_cache
        assert renderer.character_voice_cache["小明"] is not None
    
    def test_validate_storyboard_empty_chapters(self, renderer):
        from src.agents.base.exceptions import ValidationError
        
        storyboard = StoryboardResult(chapters=[], total_duration=0, total_scenes=0)
        with pytest.raises(ValidationError):
            renderer._validate_storyboard(storyboard)
    
    def test_validate_storyboard_empty_scenes(self, renderer):
        from src.agents.base.exceptions import ValidationError
        
        storyboard = StoryboardResult(
            chapters=[
                StoryboardChapter(chapter_id=1, title="Chapter 1", scenes=[])
            ],
            total_duration=0,
            total_scenes=0
        )
        with pytest.raises(ValidationError):
            renderer._validate_storyboard(storyboard)
    
    @pytest.mark.asyncio
    async def test_render_integration(self, renderer, sample_storyboard):
        with patch.object(renderer, '_call_image_generation_api', new_callable=AsyncMock) as mock_img, \
             patch.object(renderer, '_call_tts_api', new_callable=AsyncMock) as mock_tts, \
             patch.object(renderer, '_get_audio_duration', new_callable=AsyncMock) as mock_duration:
            
            mock_img.return_value = b"fake_image_data"
            mock_tts.return_value = b"fake_audio_data"
            mock_duration.return_value = 2.5
            
            with patch.object(renderer.task_storage, 'save_image', new_callable=AsyncMock) as mock_save_img, \
                 patch.object(renderer.task_storage, 'save_audio', new_callable=AsyncMock) as mock_save_audio:
                
                mock_save_img.return_value = "/path/to/image.png"
                mock_save_audio.return_value = "/path/to/audio.mp3"
                
                result = await renderer.render(sample_storyboard)
                
                assert result.total_scenes == 1
                assert len(result.chapters) == 1
                assert len(result.chapters[0].scenes) == 1
                
                rendered_scene = result.chapters[0].scenes[0]
                assert rendered_scene.image_path == "/path/to/image.png"
                assert rendered_scene.audio_path == "/path/to/audio.mp3"
                assert rendered_scene.audio_duration == 2.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
