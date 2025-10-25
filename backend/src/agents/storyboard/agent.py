from typing import Dict, List, Any, Optional
import json
import logging

from langchain_openai import ChatOpenAI

from .config import StoryboardConfig
from .exceptions import ValidationError, ProcessError, APIError
from .prompts import STORYBOARD_PROMPT_TEMPLATE
from ..base.llm_utils import LLMJSONMixin
from ..base.agent import BaseAgent

logger = logging.getLogger(__name__)


class StoryboardAgent(BaseAgent[StoryboardConfig], LLMJSONMixin):
    
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
            novel_data: 小说解析数据
            **kwargs: 其他参数
        
        Returns:
            Dict[str, Any]: 分镜数据
        """
        return await self.create(novel_data, kwargs.get("options"))
    
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
    
    async def create(
        self,
        novel_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._validate_input(novel_data)
        
        scenes = novel_data.get("scenes", [])
        characters = novel_data.get("characters", [])
        
        if not scenes:
            raise ValidationError("No scenes provided in novel_data")
        
        max_scenes = self.config.max_scenes
        if options and "max_scenes" in options:
            max_scenes = options["max_scenes"]
        
        scenes_to_process = scenes[:max_scenes]
        
        logger.info(f"Creating storyboard for {len(scenes_to_process)} scenes")
        
        storyboard_scenes = await self._design_scenes(
            scenes_to_process,
            characters
        )
        
        return {"scenes": storyboard_scenes}
    
    async def _design_scenes(
        self,
        scenes: List[Dict[str, Any]],
        characters: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        scene_info = self._format_scenes(scenes)
        characters_info = self._format_characters(characters)
        
        variables = {
            "scene_info": scene_info,
            "characters_info": characters_info,
        }
        
        try:
            storyboard_data = await self._call_llm_json(
                STORYBOARD_PROMPT_TEMPLATE,
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
            
            return enhanced_scenes
        
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
        
        return storyboard_scene
    
    def _calculate_duration(
        self,
        dialogue: List[Dict[str, str]],
        actions: List[str],
    ) -> float:
        dialogue_duration = 0.0
        for d in dialogue:
            text = d.get("text", "")
            dialogue_duration += len(text) / self.config.dialogue_chars_per_second
        
        action_duration = len(actions) * self.config.action_duration
        
        total = dialogue_duration + action_duration
        
        total = max(self.config.min_scene_duration, 
                    min(self.config.max_scene_duration, total))
        
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
        
        if "scenes" not in novel_data:
            raise ValidationError("novel_data must contain 'scenes' key")
        
        if not isinstance(novel_data["scenes"], list):
            raise ValidationError("'scenes' must be a list")
