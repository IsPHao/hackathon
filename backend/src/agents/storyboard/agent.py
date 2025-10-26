from typing import Dict, List, Any, Optional
import json
import logging

from langchain_openai import ChatOpenAI

from .config import StoryboardConfig
from ..base.exceptions import ValidationError
from .models import (
    StoryboardResult,
    StoryboardChapter,
    StoryboardScene,
    CharacterRenderInfo,
    AudioInfo,
    ImageRenderInfo,
)
from ..novel_parser.models import NovelParseResult, CharacterInfo, CharacterAppearance

logger = logging.getLogger(__name__)


class StoryboardAgent:
    
    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        config: Optional[StoryboardConfig] = None,
    ):
        self.llm = llm
        self.config = config or StoryboardConfig()
    
    async def create(
        self,
        novel_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        创建分镜数据
        
        Args:
            novel_data: 小说解析数据（NovelParseResult格式）
            options: 可选参数
        
        Returns:
            Dict[str, Any]: 分镜数据（StoryboardResult格式）
        """
        try:
            novel_result = NovelParseResult(**novel_data)
        except Exception as e:
            logger.error(f"Failed to parse NovelParseResult: {e}")
            raise ValidationError(f"Invalid NovelParseResult format: {e}") from e
        
        result = await self._convert_to_storyboard(novel_result, options)
        return result.model_dump()
    
    async def _convert_to_storyboard(
        self,
        novel_result: NovelParseResult,
        options: Optional[Dict[str, Any]] = None,
    ) -> StoryboardResult:
        storyboard_chapters = []
        total_duration = 0.0
        total_scenes = 0
        
        for chapter in novel_result.chapters:
            storyboard_scenes = []
            
            for scene in chapter.scenes:
                try:
                    storyboard_scene = self._convert_scene(
                        scene=scene,
                        chapter_id=chapter.chapter_id,
                        global_characters=novel_result.characters,
                    )
                    storyboard_scenes.append(storyboard_scene)
                    total_duration += storyboard_scene.duration
                    total_scenes += 1
                except Exception as e:
                    logger.warning(f"Failed to convert scene {scene.scene_id}: {e}. Using fallback.")
                    fallback_scene = self._create_fallback_scene(
                        scene_id=scene.scene_id,
                        chapter_id=chapter.chapter_id,
                    )
                    storyboard_scenes.append(fallback_scene)
                    total_duration += fallback_scene.duration
                    total_scenes += 1
            
            storyboard_chapter = StoryboardChapter(
                chapter_id=chapter.chapter_id,
                title=chapter.title or f"第{chapter.chapter_id}章",
                summary=chapter.summary or "",
                scenes=storyboard_scenes,
            )
            storyboard_chapters.append(storyboard_chapter)
        
        return StoryboardResult(
            chapters=storyboard_chapters,
            total_duration=round(total_duration, 1),
            total_scenes=total_scenes,
        )
    
    def _convert_scene(
        self,
        scene: Any,
        chapter_id: int,
        global_characters: List[CharacterInfo],
    ) -> StoryboardScene:
        characters = self._merge_character_info(
            scene=scene,
            global_characters=global_characters,
        )
        
        audio = self._create_audio_info(scene)
        
        image = self._create_image_info(
            scene=scene,
            characters=characters,
        )
        
        duration = self._calculate_scene_duration(audio)
        
        return StoryboardScene(
            scene_id=scene.scene_id,
            chapter_id=chapter_id,
            location=scene.location or "",
            time=scene.time or "",
            atmosphere=scene.atmosphere or "",
            description=scene.description or "",
            characters=characters,
            audio=audio,
            image=image,
            duration=duration,
            character_action=scene.character_action or "",
        )
    
    def _merge_character_info(
        self,
        scene: Any,
        global_characters: List[CharacterInfo],
    ) -> List[CharacterRenderInfo]:
        character_map = {char.name: char for char in global_characters}
        
        result = []
        for char_name in scene.characters:
            global_char = character_map.get(char_name)
            scene_appearance = scene.character_appearances.get(char_name)
            
            if scene_appearance:
                appearance = scene_appearance
            elif global_char:
                appearance = global_char.appearance
            else:
                appearance = CharacterAppearance()
            
            render_info = CharacterRenderInfo(
                name=char_name,
                gender=appearance.gender or "unknown",
                age=appearance.age,
                age_stage=appearance.age_stage or "",
                hair=appearance.hair or "",
                eyes=appearance.eyes or "",
                clothing=appearance.clothing or "",
                features=appearance.features or "",
                body_type=appearance.body_type or "",
                height=appearance.height or "",
                skin=appearance.skin or "",
                personality=global_char.personality if global_char else "",
                role=global_char.role if global_char else "",
            )
            result.append(render_info)
        
        return result
    
    def _create_audio_info(self, scene: Any) -> AudioInfo:
        if scene.content_type == "dialogue":
            text = scene.dialogue_text or ""
            speaker = scene.speaker or ""
            audio_type = "dialogue"
        else:
            text = scene.narration or ""
            speaker = "narrator"
            audio_type = "narration"
        
        config: StoryboardConfig = self.config
        estimated_duration = len(text) / config.dialogue_chars_per_second if text else 0.0
        
        return AudioInfo(
            type=audio_type,
            speaker=speaker,
            text=text,
            estimated_duration=round(estimated_duration, 1),
        )
    
    def _create_image_info(
        self,
        scene: Any,
        characters: List[CharacterRenderInfo],
    ) -> ImageRenderInfo:
        prompt_parts = ["anime style"]
        
        if scene.description:
            prompt_parts.append(scene.description)
        
        if scene.location:
            prompt_parts.append(f"location: {scene.location}")
        
        if scene.time:
            prompt_parts.append(f"time: {scene.time}")
        
        if scene.atmosphere:
            prompt_parts.append(f"atmosphere: {scene.atmosphere}")
        
        if scene.lighting:
            prompt_parts.append(f"lighting: {scene.lighting}")
        
        for char in characters:
            char_desc_parts = [char.name]
            if char.gender and char.gender != "unknown":
                char_desc_parts.append(char.gender)
            if char.age_stage:
                char_desc_parts.append(char.age_stage)
            if char.hair:
                char_desc_parts.append(char.hair)
            if char.clothing:
                char_desc_parts.append(char.clothing)
            if char.features:
                char_desc_parts.append(char.features)
            
            if len(char_desc_parts) > 1:
                prompt_parts.append(", ".join(char_desc_parts))
        
        if scene.character_action:
            prompt_parts.append(scene.character_action)
        
        prompt_parts.append("high quality, detailed, cinematic composition")
        
        prompt = ", ".join(prompt_parts)
        
        return ImageRenderInfo(
            prompt=prompt,
            negative_prompt="low quality, blurry, distorted, ugly",
            style_tags=["anime", "high quality", "detailed"],
            shot_type="medium_shot",
            camera_angle="eye_level",
            composition="rule of thirds",
            lighting=scene.lighting or "natural",
        )
    
    def _calculate_scene_duration(self, audio: AudioInfo) -> float:
        config: StoryboardConfig = self.config
        duration = audio.estimated_duration
        
        duration = max(config.min_scene_duration, min(config.max_scene_duration, duration))
        
        return round(duration, 1)
    
    def _create_fallback_scene(
        self,
        scene_id: int,
        chapter_id: int,
    ) -> StoryboardScene:
        config: StoryboardConfig = self.config
        
        return StoryboardScene(
            scene_id=scene_id,
            chapter_id=chapter_id,
            location="",
            time="",
            atmosphere="",
            description="",
            characters=[],
            audio=AudioInfo(
                type="narration",
                speaker="narrator",
                text="",
                estimated_duration=0.0,
            ),
            image=ImageRenderInfo(),
            duration=config.min_scene_duration,
            character_action="",
        )