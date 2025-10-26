from typing import Optional, Dict, Any, List
import asyncio
import logging
import uuid
import base64
import json
import hashlib
import hmac
from pathlib import Path
from urllib.parse import urlencode

import aiohttp
from aiohttp import ClientTimeout

from .config import SceneRendererConfig
from .models import (
    StoryboardResult,
    StoryboardChapter,
    StoryboardScene,
    RenderedScene,
    RenderedChapter,
    RenderResult,
    CharacterRenderInfo,
)
from ..base import TaskStorageManager
from ..base.exceptions import ValidationError, GenerationError, SynthesisError, APIError

logger = logging.getLogger(__name__)


class SceneRenderer:
    
    VOICE_TYPES = [
        {"voice_name": "甜美教学小源", "voice_type": "qiniu_zh_female_tmjxxy", "gender": "female", "age_stage": "young"},
        {"voice_name": "校园清新学姐", "voice_type": "qiniu_zh_female_xyqxxj", "gender": "female", "age_stage": "young"},
        {"voice_name": "邻家辅导学长", "voice_type": "qiniu_zh_male_ljfdxz", "gender": "male", "age_stage": "young"},
        {"voice_name": "邻家辅导学姐", "voice_type": "qiniu_zh_female_ljfdxx", "gender": "female", "age_stage": "young"},
        {"voice_name": "温婉学科讲师", "voice_type": "qiniu_zh_female_wwxkjx", "gender": "female", "age_stage": "adult"},
        {"voice_name": "率真校园向导", "voice_type": "qiniu_zh_male_szxyxd", "gender": "male", "age_stage": "young"},
        {"voice_name": "干练课堂思思", "voice_type": "qiniu_zh_female_glktss", "gender": "female", "age_stage": "adult"},
        {"voice_name": "温和学科小哥", "voice_type": "qiniu_zh_male_whxkxg", "gender": "male", "age_stage": "young"},
        {"voice_name": "温暖沉稳学长", "voice_type": "qiniu_zh_male_wncwxz", "gender": "male", "age_stage": "young"},
        {"voice_name": "开朗教学督导", "voice_type": "qiniu_zh_female_kljxdd", "gender": "female", "age_stage": "adult"},
        {"voice_name": "渊博学科男教师", "voice_type": "qiniu_zh_male_ybxknjs", "gender": "male", "age_stage": "adult"},
        {"voice_name": "火力少年凯凯", "voice_type": "qiniu_zh_male_hlsnkk", "gender": "male", "age_stage": "child"},
        {"voice_name": "通用阳光讲师", "voice_type": "qiniu_zh_male_tyygjs", "gender": "male", "age_stage": "adult"},
        {"voice_name": "知性教学女教师", "voice_type": "qiniu_zh_female_zxjxnjs", "gender": "female", "age_stage": "adult"},
        {"voice_name": "慈祥教学顾问", "voice_type": "qiniu_zh_female_cxjxgw", "gender": "female", "age_stage": "elder"},
        {"voice_name": "社区教育阿姨", "voice_type": "qiniu_zh_female_sqjyay", "gender": "female", "age_stage": "elder"},
        {"voice_name": "动漫樱桃丸子", "voice_type": "qiniu_zh_female_dmytwz", "gender": "female", "age_stage": "child"},
        {"voice_name": "少儿故事配音", "voice_type": "qiniu_zh_female_segsby", "gender": "female", "age_stage": "child"},
        {"voice_name": "轻松懒音绵宝", "voice_type": "qiniu_zh_male_qslymb", "gender": "male", "age_stage": "child"},
        {"voice_name": "活力率真萌仔", "voice_type": "qiniu_zh_male_hllzmz", "gender": "male", "age_stage": "child"},
        {"voice_name": "温婉课件配音", "voice_type": "qiniu_zh_female_wwkjby", "gender": "female", "age_stage": "adult"},
        {"voice_name": "儿童故事熊二", "voice_type": "qiniu_zh_male_etgsxe", "gender": "male", "age_stage": "child"},
        {"voice_name": "古装剧教学版", "voice_type": "qiniu_zh_male_gzjjxb", "gender": "male", "age_stage": "adult"},
        {"voice_name": "磁性课件男声", "voice_type": "qiniu_zh_male_cxkjns", "gender": "male", "age_stage": "adult"},
        {"voice_name": "趣味知识传播", "voice_type": "qiniu_zh_female_qwzscb", "gender": "female", "age_stage": "adult"},
        {"voice_name": "名著角色猴哥", "voice_type": "qiniu_zh_male_mzjsxg", "gender": "male", "age_stage": "adult"},
        {"voice_name": "英语启蒙佩奇", "voice_type": "qiniu_zh_female_yyqmpq", "gender": "female", "age_stage": "child"},
        {"voice_name": "天才少年示范", "voice_type": "qiniu_zh_male_tcsnsf", "gender": "male", "age_stage": "child"},
    ]
    
    def __init__(
        self,
        task_id: str,
        config: Optional[SceneRendererConfig] = None,
    ):
        self.task_id = task_id
        self.config = config or SceneRendererConfig()
        self.task_storage = TaskStorageManager(
            task_id,
            base_path=self.config.task_storage_base_path
        )
        self.character_voice_cache: Dict[str, str] = {}
        logger.info(f"SceneRenderer initialized for task {task_id}")
    
    async def render(self, storyboard: StoryboardResult) -> RenderResult:
        logger.info(f"Starting render for {len(storyboard.chapters)} chapters, {storyboard.total_scenes} scenes")
        
        self._validate_storyboard(storyboard)
        
        self._prepare_character_voices(storyboard)
        
        rendered_chapters = []
        total_duration = 0.0
        total_scenes = 0
        
        for chapter in storyboard.chapters:
            logger.info(f"Rendering chapter {chapter.chapter_id}: {chapter.title}")
            rendered_chapter = await self._render_chapter(chapter)
            rendered_chapters.append(rendered_chapter)
            total_duration += rendered_chapter.total_duration
            total_scenes += len(rendered_chapter.scenes)
        
        result = RenderResult(
            chapters=rendered_chapters,
            total_duration=total_duration,
            total_scenes=total_scenes,
            output_directory=str(self.task_storage.base_path)
        )
        
        logger.info(f"Render complete: {total_scenes} scenes, {total_duration:.2f}s total")
        return result
    
    async def _render_chapter(self, chapter: StoryboardChapter) -> RenderedChapter:
        rendered_scenes = []
        chapter_duration = 0.0
        
        for scene in chapter.scenes:
            logger.info(f"Rendering scene {scene.scene_id} in chapter {chapter.chapter_id}")
            rendered_scene = await self._render_scene(scene)
            rendered_scenes.append(rendered_scene)
            chapter_duration += rendered_scene.duration
        
        return RenderedChapter(
            chapter_id=chapter.chapter_id,
            title=chapter.title,
            scenes=rendered_scenes,
            total_duration=chapter_duration
        )
    
    async def _render_scene(self, scene: StoryboardScene) -> RenderedScene:
        image_task = self._generate_image(scene)
        audio_task = self._generate_audio(scene)
        
        try:
            image_path, audio_path = await asyncio.gather(image_task, audio_task)
        except Exception as e:
            logger.error(f"Failed to render scene {scene.scene_id}: {e}")
            raise GenerationError(f"Scene {scene.scene_id} rendering failed") from e
        
        audio_duration = await self._get_audio_duration(audio_path)
        
        actual_duration = max(scene.duration, audio_duration)
        
        return RenderedScene(
            scene_id=scene.scene_id,
            chapter_id=scene.chapter_id,
            image_path=image_path,
            audio_path=audio_path,
            duration=actual_duration,
            audio_duration=audio_duration,
            metadata={
                "location": scene.location,
                "time": scene.time,
                "atmosphere": scene.atmosphere,
                "characters": [char.name for char in scene.characters],
                "audio_type": scene.audio.type,
                "speaker": scene.audio.speaker,
            }
        )
    
    async def _generate_image(self, scene: StoryboardScene) -> str:
        prompt = self._build_image_prompt(scene)
        
        for attempt in range(self.config.retry_attempts):
            try:
                image_data = await self._call_image_generation_api(prompt)
                filename = f"scene_{scene.chapter_id}_{scene.scene_id}_{uuid.uuid4()}.png"
                image_path = await self.task_storage.save_image(image_data, filename)
                logger.info(f"Image generated for scene {scene.scene_id}: {image_path}")
                return image_path
            except Exception as e:
                logger.warning(f"Image generation attempt {attempt + 1}/{self.config.retry_attempts} failed: {e}")
                if attempt == self.config.retry_attempts - 1:
                    raise GenerationError(f"Failed to generate image for scene {scene.scene_id}") from e
                await asyncio.sleep(2 ** attempt)
        
        raise GenerationError(f"Failed to generate image for scene {scene.scene_id}")
    
    async def _generate_audio(self, scene: StoryboardScene) -> str:
        text = scene.audio.text
        
        if not text or len(text.strip()) == 0:
            return await self._generate_silent_audio()
        
        voice_type = self._select_voice_type(scene)
        
        for attempt in range(self.config.retry_attempts):
            try:
                audio_data = await self._call_tts_api(text, voice_type)
                filename = f"audio_{scene.chapter_id}_{scene.scene_id}_{uuid.uuid4()}.mp3"
                audio_path = await self.task_storage.save_audio(audio_data, filename)
                logger.info(f"Audio generated for scene {scene.scene_id}: {audio_path}")
                return audio_path
            except Exception as e:
                logger.warning(f"Audio generation attempt {attempt + 1}/{self.config.retry_attempts} failed: {e}")
                if attempt == self.config.retry_attempts - 1:
                    raise SynthesisError(f"Failed to generate audio for scene {scene.scene_id}") from e
                await asyncio.sleep(2 ** attempt)
        
        raise SynthesisError(f"Failed to generate audio for scene {scene.scene_id}")
    
    def _build_image_prompt(self, scene: StoryboardScene) -> str:
        base_prompt = scene.image.prompt or scene.description
        
        if not base_prompt:
            raise ValidationError(f"Scene {scene.scene_id} has no image prompt or description")
        
        style_tags = ", ".join(scene.image.style_tags) if scene.image.style_tags else "anime style"
        
        full_prompt = f"{base_prompt}, {style_tags}, {scene.image.shot_type}, {scene.image.camera_angle}, {scene.image.composition}, {scene.image.lighting}, high quality"
        
        return full_prompt
    
    def _select_voice_type(self, scene: StoryboardScene) -> str:
        if scene.audio.type == "narration":
            return self.config.narrator_voice_type
        
        speaker = scene.audio.speaker
        if speaker and speaker in self.character_voice_cache:
            return self.character_voice_cache[speaker]
        
        character = None
        for char in scene.characters:
            if char.name == speaker:
                character = char
                break
        
        if character:
            voice_type = self._match_voice_by_character(character)
            if speaker:
                self.character_voice_cache[speaker] = voice_type
            return voice_type
        
        return self.config.default_voice_type
    
    def _match_voice_by_character(self, character: CharacterRenderInfo) -> str:
        gender = character.gender.lower()
        age = character.age
        age_stage = character.age_stage.lower()
        
        age_category = "adult"
        if age is not None:
            if age < 12:
                age_category = "child"
            elif age < 25:
                age_category = "young"
            elif age >= 60:
                age_category = "elder"
            else:
                age_category = "adult"
        elif age_stage:
            if "儿童" in age_stage or "少儿" in age_stage or "child" in age_stage:
                age_category = "child"
            elif "青年" in age_stage or "学生" in age_stage or "young" in age_stage:
                age_category = "young"
            elif "老年" in age_stage or "elder" in age_stage:
                age_category = "elder"
            else:
                age_category = "adult"
        
        matching_voices = [
            v for v in self.VOICE_TYPES
            if v.get("gender") == gender and v.get("age_stage") == age_category
        ]
        
        if matching_voices:
            return matching_voices[0]["voice_type"]
        
        gender_voices = [
            v for v in self.VOICE_TYPES
            if v.get("gender") == gender
        ]
        
        if gender_voices:
            return gender_voices[0]["voice_type"]
        
        return self.config.default_voice_type
    
    def _prepare_character_voices(self, storyboard: StoryboardResult):
        for chapter in storyboard.chapters:
            for scene in chapter.scenes:
                if scene.audio.type == "dialogue" and scene.audio.speaker:
                    speaker = scene.audio.speaker
                    if speaker not in self.character_voice_cache:
                        for char in scene.characters:
                            if char.name == speaker:
                                voice_type = self._match_voice_by_character(char)
                                self.character_voice_cache[speaker] = voice_type
                                logger.info(f"Assigned voice {voice_type} to character {speaker}")
                                break
    
    async def _call_image_generation_api(self, prompt: str) -> bytes:
        params = {
            "model": self.config.image_model,
            "prompt": prompt,
            "size": self.config.image_size,
        }
        
        headers = {
            "Authorization": f"Bearer {self.config.qiniu_api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.config.qiniu_endpoint}/v1/images/generations"
        
        timeout = ClientTimeout(total=self.config.timeout)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise APIError(f"Qiniu Image API error: {response.status} - {error_text}")
                
                result = await response.json()
                
                if "data" not in result or not result["data"]:
                    raise GenerationError("Invalid response from Qiniu API: no image data")
                
                image_b64 = result["data"][0].get("b64_json")
                if not image_b64:
                    raise GenerationError("Invalid response from Qiniu API: no base64 image data")
                
                image_data = base64.b64decode(image_b64)
                return image_data
    
    async def _call_tts_api(self, text: str, voice_type: str) -> bytes:
        params = {
            "audio": {
                "voice_type": voice_type,
                "encoding": self.config.tts_encoding,
                "speed_ratio": self.config.tts_speed_ratio
            },
            "request": {
                "text": text
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.config.qiniu_api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.config.qiniu_endpoint}/v1/voice/tts"
        
        timeout = ClientTimeout(total=self.config.timeout)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise APIError(f"Qiniu TTS API error: {response.status} - {error_text}")
                
                result = await response.json()
                
                if "data" not in result:
                    raise SynthesisError("Invalid response from Qiniu TTS API: no audio data")
                
                audio_b64 = result["data"]
                if not audio_b64:
                    raise SynthesisError("Invalid response from Qiniu TTS API: no base64 audio data")
                
                audio_data = base64.b64decode(audio_b64)
                return audio_data
    
    async def _generate_silent_audio(self) -> str:
        try:
            import subprocess
            
            filename = f"silent_{uuid.uuid4()}.mp3"
            temp_path = self.task_storage.temp_dir / filename
            
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "lavfi",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t", str(self.config.silent_audio_duration),
                "-q:a", "9",
                str(temp_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.warning(f"FFmpeg silent audio generation failed: {error_msg}")
                temp_path.write_bytes(b"")
            
            final_path = await self.task_storage.save_audio(temp_path.read_bytes(), filename)
            
            if temp_path.exists():
                temp_path.unlink()
            
            return final_path
            
        except Exception as e:
            logger.warning(f"Failed to generate silent audio: {e}")
            filename = f"silent_{uuid.uuid4()}.mp3"
            return await self.task_storage.save_audio(b"", filename)
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        try:
            import subprocess
            
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                duration_str = stdout.decode().strip()
                return float(duration_str)
            else:
                logger.warning(f"Failed to get audio duration: {stderr.decode()}")
                return 3.0
                
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")
            return 3.0
    
    def _validate_storyboard(self, storyboard: StoryboardResult):
        if not storyboard.chapters:
            raise ValidationError("Storyboard must contain at least one chapter")
        
        for chapter in storyboard.chapters:
            if not chapter.scenes:
                raise ValidationError(f"Chapter {chapter.chapter_id} must contain at least one scene")
            
            for scene in chapter.scenes:
                if not scene.audio:
                    raise ValidationError(f"Scene {scene.scene_id} must have audio information")
