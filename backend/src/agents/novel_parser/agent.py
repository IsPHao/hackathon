from typing import Dict, List, Any, Optional
import json
import logging
import copy
from collections import defaultdict

from langchain_openai import ChatOpenAI

from .config import NovelParserConfig
from ..base.exceptions import ValidationError, ParseError, APIError
from .prompts import (
    NOVEL_PARSE_PROMPT_TEMPLATE,
    CHARACTER_APPEARANCE_ENHANCE_PROMPT_TEMPLATE,
)
from ..base.llm_utils import call_llm_json
from ..base.agent import BaseAgent

logger = logging.getLogger(__name__)


class NovelParserAgent(BaseAgent[NovelParserConfig]):
    """
    小说解析Agent
    
    负责解析小说文本，提取角色、场景和情节要点。
    支持简单模式和增强模式（分块处理长文本）。
    
    Attributes:
        llm: 语言模型客户端
        config: 配置对象
    """
    
    def __init__(
        self,
        llm: ChatOpenAI,
        config: Optional[NovelParserConfig] = None,
    ):
        super().__init__(config)
        self.llm = llm
    
    def _default_config(self) -> NovelParserConfig:
        return NovelParserConfig()
    
    async def execute(self, novel_text: str, mode: str = "simple", **kwargs) -> Dict[str, Any]:
        """
        执行小说解析(统一接口)
        
        Args:
            novel_text: 小说文本
            mode: 解析模式
            **kwargs: 其他参数
        
        Returns:
            Dict[str, Any]: 解析结果
        """
        return await self.parse(novel_text, mode, kwargs.get("options"))
    
    async def health_check(self) -> bool:
        """
        健康检查:测试LLM连接
        """
        try:
            test_messages = [("user", "test")]
            await self.llm.ainvoke(test_messages)
            self.logger.info("NovelParserAgent health check: OK")
            return True
        except Exception as e:
            self.logger.error(f"NovelParserAgent health check failed: {e}")
            return False
    
    async def parse(
        self,
        novel_text: str,
        mode: str = "enhanced",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        解析小说文本
        
        Args:
            novel_text: 小说原文
            mode: 解析模式，'simple'或'enhanced'
            options: 额外配置选项
        
        Returns:
            Dict[str, Any]: 包含characters, scenes, plot_points等键的字典
        
        Raises:
            ValidationError: 输入验证失败
            ParseError: 解析失败
        """
        self._validate_input(novel_text)
        
        if mode not in ["enhanced", "simple"]:
            raise ValidationError(f"Invalid mode: {mode}. Must be 'enhanced' or 'simple'")
        
        if mode == "enhanced":
            result = await self._parse_enhanced(novel_text, options)
        else:
            result = await self._parse_simple(novel_text, options)
        
        # 角色增强功能
        config: NovelParserConfig = self.config  # type: ignore
        if config.enable_character_enhancement and result.get("characters"):
            result["characters"] = await self._enhance_characters(result["characters"])
        
        self._validate_output(result)
        
        return result
    
    async def _parse_simple(
        self,
        novel_text: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        variables = self._build_variables(novel_text, options)
        
        try:
            parsed_data = await call_llm_json(
                llm=self.llm,
                prompt_template=NOVEL_PARSE_PROMPT_TEMPLATE,
                variables=variables,
                parse_error_class=ParseError,
                api_error_class=APIError
            )
            return parsed_data
        except Exception as e:
            logger.error(f"Failed to parse novel: {e}")
            raise ParseError(f"Failed to parse novel: {e}") from e
    
    async def _parse_enhanced(
        self,
        novel_text: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        chunks = self._split_text_into_chunks(novel_text)
        chunk_results = []
        
        for i, chunk in enumerate(chunks):
            variables = self._build_variables(chunk, options)
            
            try:
                parsed_chunk = await call_llm_json(
                    llm=self.llm,
                    prompt_template=NOVEL_PARSE_PROMPT_TEMPLATE,
                    variables=variables,
                    parse_error_class=ParseError,
                    api_error_class=APIError
                )
                chunk_results.append(parsed_chunk)
            except Exception as e:
                logger.error(f"Failed to parse chunk {i}: {e}")
                raise ParseError(f"Failed to parse chunk {i}: {e}") from e
        
        merged_result = self._merge_results(chunk_results)
        return merged_result
    
    def _split_text_into_chunks(self, text: str, chunk_size: int = 4000) -> List[str]:
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            if current_length + para_length > chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length
        
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        
        return chunks
    
    def _merge_results(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        character_map = defaultdict(list)
        all_scenes = []
        all_plot_points = []
        
        scene_offset = 0
        for chunk_result in chunk_results:
            for char in chunk_result.get("characters", []):
                character_map[char["name"]].append(char)
            
            for scene in chunk_result.get("scenes", []):
                scene["scene_id"] += scene_offset
                all_scenes.append(scene)
            
            for plot_point in chunk_result.get("plot_points", []):
                plot_point["scene_id"] += scene_offset
                all_plot_points.append(plot_point)
            
            if chunk_result.get("scenes"):
                scene_offset += len(chunk_result["scenes"])
        
        merged_characters = []
        for name, occurrences in character_map.items():
            if len(occurrences) == 1:
                merged_characters.append(occurrences[0])
            else:
                merged_char = self._merge_character_occurrences(occurrences)
                merged_characters.append(merged_char)
        
        return {
            "characters": merged_characters,
            "scenes": all_scenes,
            "plot_points": all_plot_points,
        }
    
    def _merge_character_occurrences(self, occurrences: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not occurrences:
            return {}
        
        base_char = copy.deepcopy(occurrences[0])
        all_descriptions = []
        all_personalities = []
        
        for occ in occurrences:
            if occ.get("description"):
                all_descriptions.append(occ["description"])
            
            if occ.get("personality"):
                all_personalities.append(occ["personality"])
            
            for key, value in occ.get("appearance", {}).items():
                if value and (not base_char["appearance"].get(key) or 
                            len(str(value)) > len(str(base_char["appearance"].get(key, "")))):
                    base_char["appearance"][key] = value
        
        if all_descriptions:
            base_char["description"] = " ".join(set(all_descriptions))
        if all_personalities:
            base_char["personality"] = ", ".join(set(all_personalities))
        
        return base_char
    
    def _validate_input(self, novel_text: str):
        config: NovelParserConfig = self.config  # type: ignore
        if not novel_text or len(novel_text.strip()) < config.min_text_length:
            raise ValidationError(
                f"Novel text too short. Minimum {config.min_text_length} characters required"
            )
        
        if len(novel_text) > config.max_text_length:
            raise ValidationError(
                f"Novel text too long. Maximum {config.max_text_length} characters allowed"
            )
    
    def _build_variables(
        self,
        novel_text: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """构建 LangChain prompt 变量字典"""
        config: NovelParserConfig = self.config  # type: ignore
        max_characters = config.max_characters
        max_scenes = config.max_scenes
        
        if options:
            max_characters = options.get("max_characters", max_characters)
            max_scenes = options.get("max_scenes", max_scenes)
        
        return {
            "novel_text": novel_text,
            "max_characters": max_characters,
            "max_scenes": max_scenes,
        }
    
    
    async def _enhance_characters(
        self, characters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        enhanced_characters = []
        
        for char in characters:
            visual_desc = await self._generate_visual_description(char)
            char["visual_description"] = visual_desc
            enhanced_characters.append(char)
        
        return enhanced_characters
    
    async def _generate_visual_description(
        self, character: Dict[str, Any]
    ) -> Dict[str, Any]:  # Changed return type
        variables = {
            "name": character.get("name", "Unknown"),
            "description": character.get("description", ""),
            "appearance": json.dumps(character.get("appearance", {}), ensure_ascii=False),
        }
        
        try:
            response = await call_llm_json(
                llm=self.llm,
                prompt_template=CHARACTER_APPEARANCE_ENHANCE_PROMPT_TEMPLATE,
                variables=variables,
                parse_error_class=ParseError,
                api_error_class=APIError
            )
            return response
        except Exception as e:
            logger.warning(f"Failed to generate visual description for {character.get('name')}: {e}")
            return {
                "prompt": "",
                "negative_prompt": "low quality, blurry",
                "style_tags": ["anime"],
            }
    
    def _validate_output(self, data: Dict[str, Any]):
        required_keys = ["characters", "scenes", "plot_points"]
        for key in required_keys:
            if key not in data:
                raise ValidationError(f"Missing required key: {key}")
        
        if not data["characters"]:
            raise ValidationError("No characters extracted")
        
        if not data["scenes"]:
            raise ValidationError("No scenes extracted")