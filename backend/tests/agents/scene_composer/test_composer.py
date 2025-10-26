import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
import asyncio

from src.agents.scene_composer import SceneComposer, SceneComposerConfig
from src.agents.scene_renderer.models import (
    RenderResult,
    RenderedChapter,
    RenderedScene,
)
from src.agents.base.exceptions import ValidationError, CompositionError


@pytest.fixture
def config():
    return SceneComposerConfig(
        timeout=600,
        codec="libx264",
        preset="medium",
        audio_codec="aac",
        audio_bitrate="192k",
        task_storage_base_path="./test_data/scene_composer",
        final_output_dir="./test_data/scene_composer/final_output",
        uuid_suffix_length=8
    )


@pytest.fixture
def composer(config):
    return SceneComposer(task_id="test_task_123", config=config)


@pytest.fixture
def sample_rendered_scene():
    return RenderedScene(
        scene_id=1,
        chapter_id=1,
        image_path="/path/to/image1.png",
        audio_path="/path/to/audio1.mp3",
        duration=3.0,
        audio_duration=2.5
    )


@pytest.fixture
def sample_rendered_scene_no_audio():
    return RenderedScene(
        scene_id=2,
        chapter_id=1,
        image_path="/path/to/image2.png",
        audio_path="",
        duration=3.0,
        audio_duration=0.0
    )


@pytest.fixture
def sample_rendered_scene_long_audio():
    return RenderedScene(
        scene_id=3,
        chapter_id=1,
        image_path="/path/to/image3.png",
        audio_path="/path/to/audio3.mp3",
        duration=2.0,
        audio_duration=5.0
    )


@pytest.fixture
def sample_render_result(sample_rendered_scene):
    return RenderResult(
        chapters=[
            RenderedChapter(
                chapter_id=1,
                title="第一章",
                scenes=[sample_rendered_scene],
                total_duration=3.0
            )
        ],
        total_duration=3.0,
        total_scenes=1,
        output_directory="/path/to/output"
    )


@pytest.fixture
def multi_scene_render_result(
    sample_rendered_scene,
    sample_rendered_scene_no_audio,
    sample_rendered_scene_long_audio
):
    return RenderResult(
        chapters=[
            RenderedChapter(
                chapter_id=1,
                title="第一章",
                scenes=[
                    sample_rendered_scene,
                    sample_rendered_scene_no_audio,
                    sample_rendered_scene_long_audio
                ],
                total_duration=8.0
            )
        ],
        total_duration=8.0,
        total_scenes=3,
        output_directory="/path/to/output"
    )


class TestSceneComposer:
    
    def test_initialization(self, composer, config):
        assert composer.task_id == "test_task_123"
        assert composer.config == config
        assert composer.temp_dir is not None
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, composer):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = await composer.health_check()
            assert result is True
            assert mock_run.call_count == 2
    
    @pytest.mark.asyncio
    async def test_health_check_ffmpeg_missing(self, composer):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=1),
                MagicMock(returncode=0)
            ]
            result = await composer.health_check()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check_ffprobe_missing(self, composer):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),
                MagicMock(returncode=1)
            ]
            result = await composer.health_check()
            assert result is False
    
    def test_validate_input_valid(self, composer, sample_render_result):
        composer._validate_input(sample_render_result)
    
    def test_validate_input_not_render_result(self, composer):
        with pytest.raises(ValidationError):
            composer._validate_input("not a render result")
    
    def test_validate_input_no_chapters(self, composer):
        render_result = RenderResult(
            chapters=[],
            total_duration=0,
            total_scenes=0,
            output_directory="/path"
        )
        with pytest.raises(ValidationError):
            composer._validate_input(render_result)
    
    def test_validate_input_no_scenes(self, composer):
        render_result = RenderResult(
            chapters=[
                RenderedChapter(
                    chapter_id=1,
                    title="Chapter 1",
                    scenes=[],
                    total_duration=0
                )
            ],
            total_duration=0,
            total_scenes=0,
            output_directory="/path"
        )
        with pytest.raises(ValidationError):
            composer._validate_input(render_result)
    
    def test_validate_input_no_image_path(self, composer):
        render_result = RenderResult(
            chapters=[
                RenderedChapter(
                    chapter_id=1,
                    title="Chapter 1",
                    scenes=[
                        RenderedScene(
                            scene_id=1,
                            chapter_id=1,
                            image_path="",
                            audio_path="/audio.mp3",
                            duration=3.0
                        )
                    ],
                    total_duration=3.0
                )
            ],
            total_duration=3.0,
            total_scenes=1,
            output_directory="/path"
        )
        with pytest.raises(ValidationError):
            composer._validate_input(render_result)
    
    def test_build_scene_ffmpeg_cmd_with_audio(self, composer):
        cmd = composer._build_scene_ffmpeg_cmd(
            image_path="/path/to/image.png",
            audio_path="/path/to/audio.mp3",
            output_path="/path/to/output.mp4",
            duration=3.0
        )
        assert "ffmpeg" in cmd
        assert "-i" in cmd
        assert "/path/to/image.png" in cmd
        assert "/path/to/audio.mp3" in cmd
        assert "/path/to/output.mp4" in cmd
        assert "-t" in cmd
        assert "3.0" in cmd
    
    def test_build_scene_ffmpeg_cmd_without_audio(self, composer):
        cmd = composer._build_scene_ffmpeg_cmd(
            image_path="/path/to/image.png",
            audio_path=None,
            output_path="/path/to/output.mp4",
            duration=3.0
        )
        assert "ffmpeg" in cmd
        assert "-i" in cmd
        assert "/path/to/image.png" in cmd
        assert any("anullsrc" in item for item in cmd)
        assert "/path/to/output.mp4" in cmd
    
    def test_build_concat_ffmpeg_cmd(self, composer):
        cmd = composer._build_concat_ffmpeg_cmd(
            concat_list_path="/path/to/concat.txt",
            output_path="/path/to/output.mp4"
        )
        assert "ffmpeg" in cmd
        assert "-f" in cmd
        assert "concat" in cmd
        assert "/path/to/concat.txt" in cmd
        assert "/path/to/output.mp4" in cmd
    
    @pytest.mark.asyncio
    async def test_compose_scene_with_audio(self, composer, sample_rendered_scene):
        with patch('os.path.exists', return_value=True), \
             patch('asyncio.create_subprocess_exec') as mock_process:
            
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_process.return_value = mock_proc
            
            result = await composer._compose_scene(sample_rendered_scene)
            assert result is not None
            assert "scene_1_" in result
            assert ".mp4" in result
    
    @pytest.mark.asyncio
    async def test_compose_scene_without_audio(self, composer, sample_rendered_scene_no_audio):
        with patch('os.path.exists') as mock_exists, \
             patch('asyncio.create_subprocess_exec') as mock_process:
            
            mock_exists.side_effect = lambda path: path == sample_rendered_scene_no_audio.image_path
            
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_process.return_value = mock_proc
            
            result = await composer._compose_scene(sample_rendered_scene_no_audio)
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_compose_scene_audio_longer_than_duration(
        self, composer, sample_rendered_scene_long_audio
    ):
        with patch('os.path.exists', return_value=True), \
             patch('asyncio.create_subprocess_exec') as mock_process:
            
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_process.return_value = mock_proc
            
            result = await composer._compose_scene(sample_rendered_scene_long_audio)
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_compose_scene_image_not_found(self, composer, sample_rendered_scene):
        with patch('os.path.exists', return_value=False):
            with pytest.raises(CompositionError):
                await composer._compose_scene(sample_rendered_scene)
    
    @pytest.mark.asyncio
    async def test_compose_scene_ffmpeg_timeout(self, composer, sample_rendered_scene):
        with patch('os.path.exists', return_value=True), \
             patch('asyncio.create_subprocess_exec') as mock_process:
            
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_proc.kill = MagicMock()
            mock_proc.wait = AsyncMock()
            mock_process.return_value = mock_proc
            
            with pytest.raises(CompositionError) as exc_info:
                await composer._compose_scene(sample_rendered_scene)
            assert "timed out" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_compose_scene_ffmpeg_error(self, composer, sample_rendered_scene):
        with patch('os.path.exists', return_value=True), \
             patch('asyncio.create_subprocess_exec') as mock_process:
            
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b"FFmpeg error"))
            mock_proc.returncode = 1
            mock_process.return_value = mock_proc
            
            with pytest.raises(CompositionError):
                await composer._compose_scene(sample_rendered_scene)
    
    @pytest.mark.asyncio
    async def test_concatenate_videos(self, composer):
        video_paths = ["/path/to/video1.mp4", "/path/to/video2.mp4"]
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.abspath', side_effect=lambda x: x), \
             patch('asyncio.create_subprocess_exec') as mock_process, \
             patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'unlink'):
            
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_process.return_value = mock_proc
            
            result = await composer._concatenate_videos(video_paths, "test_output")
            assert result is not None
            assert "test_output_" in result
            assert ".mp4" in result
    
    @pytest.mark.asyncio
    async def test_concatenate_videos_cleanup_on_error(self, composer):
        video_paths = ["/path/to/video1.mp4", "/path/to/video2.mp4"]
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.abspath', side_effect=lambda x: x), \
             patch('asyncio.create_subprocess_exec') as mock_process, \
             patch.object(Path, 'exists', return_value=True) as mock_exists, \
             patch.object(Path, 'unlink') as mock_unlink:
            
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b"Error"))
            mock_proc.returncode = 1
            mock_process.return_value = mock_proc
            
            with pytest.raises(CompositionError):
                await composer._concatenate_videos(video_paths, "test_output")
            
            mock_unlink.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_video_duration_success(self, composer):
        with patch('asyncio.create_subprocess_exec') as mock_process:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(
                return_value=(b'{"format": {"duration": "10.5"}}', b"")
            )
            mock_proc.returncode = 0
            mock_process.return_value = mock_proc
            
            duration = await composer._get_video_duration("/path/to/video.mp4")
            assert duration == 10.5
    
    @pytest.mark.asyncio
    async def test_get_video_duration_failure(self, composer):
        with patch('asyncio.create_subprocess_exec') as mock_process:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b"Error"))
            mock_proc.returncode = 1
            mock_process.return_value = mock_proc
            
            duration = await composer._get_video_duration("/path/to/video.mp4")
            assert duration == 0.0
    
    @pytest.mark.asyncio
    async def test_compose_chapter_single_scene(self, composer, sample_rendered_scene):
        with patch.object(composer, '_compose_scene', new_callable=AsyncMock) as mock_compose:
            mock_compose.return_value = "/path/to/scene_video.mp4"
            
            chapter = RenderedChapter(
                chapter_id=1,
                title="Chapter 1",
                scenes=[sample_rendered_scene],
                total_duration=3.0
            )
            
            result = await composer._compose_chapter(chapter)
            assert result == "/path/to/scene_video.mp4"
    
    @pytest.mark.asyncio
    async def test_compose_chapter_cleanup_scene_videos(
        self, composer, sample_rendered_scene, sample_rendered_scene_no_audio
    ):
        with patch.object(composer, '_compose_scene', new_callable=AsyncMock) as mock_compose, \
             patch.object(composer, '_concatenate_videos', new_callable=AsyncMock) as mock_concat, \
             patch('os.path.exists', return_value=True), \
             patch('os.unlink') as mock_unlink:
            
            mock_compose.side_effect = [
                "/path/to/scene1.mp4",
                "/path/to/scene2.mp4"
            ]
            mock_concat.return_value = "/path/to/chapter.mp4"
            
            chapter = RenderedChapter(
                chapter_id=1,
                title="Chapter 1",
                scenes=[sample_rendered_scene, sample_rendered_scene_no_audio],
                total_duration=6.0
            )
            
            result = await composer._compose_chapter(chapter)
            assert result == "/path/to/chapter.mp4"
            assert mock_unlink.call_count == 2
    
    @pytest.mark.asyncio
    async def test_compose_integration(self, composer, sample_render_result):
        with patch.object(composer, '_compose_scene', new_callable=AsyncMock) as mock_scene, \
             patch.object(composer, '_get_video_duration', new_callable=AsyncMock) as mock_duration, \
             patch('os.path.getsize', return_value=1024000), \
             patch.object(composer, '_persist_final_video', return_value="/path/to/final_test.mp4"):
            
            mock_scene.return_value = "/path/to/scene_video.mp4"
            mock_duration.return_value = 3.0
            
            result = await composer.compose(sample_render_result)
            
            assert result["video_path"] == "/path/to/final_test.mp4"
            assert result["duration"] == 3.0
            assert result["file_size"] == 1024000
            assert result["total_scenes"] == 1
            assert result["total_chapters"] == 1
    


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
