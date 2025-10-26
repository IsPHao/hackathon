from typing import Dict, List, Any, Optional
import json
import logging

from langchain_openai import ChatOpenAI

from .config import StoryboardConfig
from ..base.exceptions import ValidationError, ProcessError, APIError
from .prompts import STORYBOARD_PROMPT_TEMPLATE
from ..base.llm_utils import call_llm_json
from ..base.agent import BaseAgent
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


class StoryboardAgent(BaseAgent[StoryboardConfig]):
    
    def __init__(
        self,
        llm: ChatOpenAI,
        config: Optional[StoryboardConfig] = None,
    ):
        super().__init__(config)
        self.llm = llm
    
    def _default_config(self) -> StoryboardConfig:
        return StoryboardConfig()
    
    async def execute(self, novel_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        执行分镜设计(统一接口)
        
        Args:
            novel_data: 小说解析数据（NovelParseResult格式）
            **kwargs: 其他参数
        
        Returns:
            Dict[str, Any]: 分镜数据（StoryboardResult格式）
        """
        result = await self.create_from_novel_result(novel_data, kwargs.get("options"))
        return result.model_dump()
    
    async def health_check(self) -> bool:
        """健康检查:测试LLM连接"""
        try:
            test_messages = [("user", "test")]
            await self.llm.ainvoke(test_messages)
            self.logger.info("StoryboardAgent health check: OK")
            return True
        except Exception as e:
            self.logger.error(f"StoryboardAgent health check failed: {e}")
            return False
    
    async def create_from_novel_result(
        self,
        novel_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> StoryboardResult:
        try:
            novel_result = NovelParseResult(**novel_data)
        except Exception as e:
            logger.error(f"Failed to parse NovelParseResult: {e}")
            raise ValidationError(f"Invalid NovelParseResult format: {e}") from e
        
        return await self._convert_to_storyboard(novel_result, options)
    
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
    
    async def create(
        self,
        novel_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._validate_input(novel_data)
        
        scenes = novel_data.get("scenes", [])
        characters = novel_data.get("characters", [])
        
        scenes_info = self._format_scenes(scenes)
        characters_info = self._format_characters(characters)
        
        variables = {
            "scene_info": scenes_info,
            "characters_info": characters_info,
        }
        
        try:
            storyboard_data = await call_llm_json(
                llm=self.llm,
                prompt_template=STORYBOARD_PROMPT_TEMPLATE,
                variables=variables,
                parse_error_class=ProcessError,
                api_error_class=APIError
            )
            storyboard_scenes = storyboard_data.get("scenes", [])
            
            enhanced_scenes = []
            for i, scene in enumerate(storyboard_scenes):
                original_scene = scenes[i] if i < len(scenes) else {}
                enhanced_scene = self._enhance_scene(scene, original_scene)
                enhanced_scenes.append(enhanced_scene)
            
            return {"scenes": enhanced_scenes}
        
        except Exception as e:
            logger.error(f"Failed to design scenes: {e}")
            raise ProcessError(f"Failed to design scenes: {e}") from e
    
    def _enhance_scene(
        self,
        storyboard_scene: Dict[str, Any],
        original_scene: Dict[str, Any],
    ) -> Dict[str, Any]:
        dialogue = original_scene.get("dialogue", [])
        actions = original_scene.get("actions", [])
        
        calculated_duration = self._calculate_duration(dialogue, actions)
        
        if "duration" not in storyboard_scene or storyboard_scene["duration"] == 0:
            storyboard_scene["duration"] = calculated_duration
        
        if "image_prompt" in storyboard_scene:
            storyboard_scene["image_prompt"] = self._enhance_image_prompt(
                storyboard_scene["image_prompt"],
                original_scene
            )
            
        # 添加对话信息到分镜场景中
        storyboard_scene["dialogue"] = dialogue
        
        return storyboard_scene
    
    def _calculate_duration(
        self,
        dialogue: List[Dict[str, str]],
        actions: List[str],
    ) -> float:
        config: StoryboardConfig = self.config  # type: ignore
        dialogue_duration = 0.0
        for d in dialogue:
            text = d.get("text", "")
            dialogue_duration += len(text) / config.dialogue_chars_per_second
        
        action_duration = len(actions) * config.action_duration
        
        total = dialogue_duration + action_duration
        
        total = max(config.min_scene_duration, 
                    min(config.max_scene_duration, total))
        
        return round(total, 1)
    
    def _enhance_image_prompt(
        self,
        base_prompt: str,
        scene: Dict[str, Any],
    ) -> str:
        prompt_parts = [
            "anime style",
            base_prompt,
            f"location: {scene.get('location', '')}",
            f"time: {scene.get('time', '')}",
            f"atmosphere: {scene.get('atmosphere', '')}",
            "high quality, detailed, cinematic composition",
        ]
        
        return ", ".join([p for p in prompt_parts if p and p != "location: " and p != "time: " and p != "atmosphere: "])
    
    def _format_scenes(self, scenes: List[Dict[str, Any]]) -> str:
        formatted = []
        for scene in scenes:
            scene_str = f"""
场景 {scene.get('scene_id', 'N/A')}:
- 地点: {scene.get('location', 'N/A')}
- 时间: {scene.get('time', 'N/A')}
- 角色: {', '.join(scene.get('characters', []))}
- 描述: {scene.get('description', 'N/A')}
- 对话: {json.dumps(scene.get('dialogue', []), ensure_ascii=False)}
- 动作: {', '.join(scene.get('actions', []))}
- 氛围: {scene.get('atmosphere', 'N/A')}
"""
            formatted.append(scene_str.strip())
        
        return "\n\n".join(formatted)
    
    def _format_characters(self, characters: List[Dict[str, Any]]) -> str:
        formatted = []
        for char in characters:
            appearance = char.get("appearance", {})
            char_str = f"""
角色: {char.get('name', 'N/A')}
- 描述: {char.get('description', 'N/A')}
- 外貌: {json.dumps(appearance, ensure_ascii=False)}
- 性格: {char.get('personality', 'N/A')}
"""
            formatted.append(char_str.strip())
        
        return "\n\n".join(formatted)
    
    
    def _validate_input(self, novel_data: Dict[str, Any]):
        if not novel_data:
            raise ValidationError("novel_data cannot be empty")
        
        if "chapters" not in novel_data and "scenes" not in novel_data:
            raise ValidationError("novel_data must contain 'chapters' or 'scenes' key")
        
        if "chapters" in novel_data:
            if not isinstance(novel_data["chapters"], list):
                raise ValidationError("'chapters' must be a list")
            if not novel_data["chapters"]:
                raise ValidationError("No chapters provided")
        elif "scenes" in novel_data:
            if not isinstance(novel_data["scenes"], list):
                raise ValidationError("'scenes' must be a list")
            if not novel_data["scenes"]:
                raise ValidationError("No scenes provided")