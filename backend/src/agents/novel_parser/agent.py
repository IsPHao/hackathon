from typing import Dict, List, Any, Optional
import json
import logging
import copy
from collections import defaultdict

from langchain_openai import ChatOpenAI

from .config import NovelParserConfig
from .models import NovelData, Character, Scene, PlotPoint, CharacterAppearance, Dialogue, VisualDescription
from ..base.exceptions import ValidationError, ParseError, APIError
from .prompts import (
    NOVEL_PARSE_PROMPT_TEMPLATE,
    CHARACTER_APPEARANCE_ENHANCE_PROMPT_TEMPLATE,
)
from ..base.llm_utils import call_llm_json

logger = logging.getLogger(__name__)


class NovelParserAgent:
    """
    Novel Parser Agent - Refactored version
    
    Parses novel text and extracts characters, scenes, and plot points.
    No longer inherits from BaseAgent, uses direct input/output with NovelData.
    
    Attributes:
        llm: Language model client
        config: Configuration object
        logger: Logger instance
    """
    
    def __init__(
        self,
        novel_text: str,
        config: NovelParserConfig,
        llm: ChatOpenAI,
    ):
        """
        Initialize NovelParserAgent
        
        Args:
            novel_text: Novel text to parse
            config: Configuration for parsing
            llm: LLM instance (created via llm_factory)
        """
        self.novel_text = novel_text
        self.config = config
        self.llm = llm
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def parse(self, mode: str = "enhanced") -> NovelData:
        """
        Parse novel text and return structured NovelData
        
        Args:
            mode: Parsing mode, 'simple' or 'enhanced'
        
        Returns:
            NovelData: Structured novel data containing characters, scenes, and plot points
        
        Raises:
            ValidationError: Input validation failed
            ParseError: Parsing failed
        """
        self._validate_input(self.novel_text)
        
        if mode not in ["enhanced", "simple"]:
            raise ValidationError(f"Invalid mode: {mode}. Must be 'enhanced' or 'simple'")
        
        if mode == "enhanced":
            result_dict = await self._parse_enhanced(self.novel_text)
        else:
            result_dict = await self._parse_simple(self.novel_text)
        
        if self.config.enable_character_enhancement and result_dict.get("characters"):
            result_dict["characters"] = await self._enhance_characters(result_dict["characters"])
        
        self._validate_output(result_dict)
        
        novel_data = NovelData.from_dict(result_dict)
        
        return novel_data
    
    async def _parse_simple(
        self,
        novel_text: str,
    ) -> Dict[str, Any]:
        variables = self._build_variables(novel_text)
        
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
    ) -> Dict[str, Any]:
        chunks = self._split_text_into_chunks(novel_text)
        chunk_results = []
        
        for i, chunk in enumerate(chunks):
            variables = self._build_variables(chunk)
            
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
        if not text or not text.strip():
            raise ValidationError("Cannot split empty text into chunks")
        
        if chunk_size <= 0:
            raise ValidationError(f"Chunk size must be positive, got {chunk_size}")
        
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
        
        if not chunks:
            raise ValidationError("Text splitting resulted in zero chunks")
        
        return chunks
    
    def _merge_results(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not chunk_results:
            raise ValidationError("Cannot merge empty chunk results")
        
        character_map = defaultdict(list)
        all_scenes = []
        all_plot_points = []
        
        scene_offset = 0
        for i, chunk_result in enumerate(chunk_results):
            if not isinstance(chunk_result, dict):
                raise ValidationError(f"Chunk result {i} is not a dictionary")
            
            try:
                for char in chunk_result.get("characters", []):
                    if not char.get("name"):
                        logger.warning(f"Character in chunk {i} missing name, skipping")
                        continue
                    character_map[char["name"]].append(char)
                
                for scene in chunk_result.get("scenes", []):
                    scene["scene_id"] += scene_offset
                    all_scenes.append(scene)
                
                for plot_point in chunk_result.get("plot_points", []):
                    plot_point["scene_id"] += scene_offset
                    all_plot_points.append(plot_point)
                
                if chunk_result.get("scenes"):
                    scene_offset += len(chunk_result["scenes"])
            except (KeyError, TypeError) as e:
                raise ValidationError(f"Error processing chunk {i}: {e}") from e
        
        merged_characters = []
        for name, occurrences in character_map.items():
            try:
                if len(occurrences) == 1:
                    merged_characters.append(occurrences[0])
                else:
                    merged_char = self._merge_character_occurrences(occurrences)
                    merged_characters.append(merged_char)
            except Exception as e:
                logger.error(f"Failed to merge character '{name}': {e}")
                merged_characters.append(occurrences[0])
        
        return {
            "characters": merged_characters,
            "scenes": all_scenes,
            "plot_points": all_plot_points,
        }
    
    def _merge_character_occurrences(self, occurrences: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not occurrences:
            raise ValidationError("Cannot merge empty character occurrences")
        
        try:
            base_char = copy.deepcopy(occurrences[0])
        except Exception as e:
            raise ValidationError(f"Failed to copy character data: {e}") from e
        
        if not isinstance(base_char, dict):
            raise ValidationError("Character occurrence must be a dictionary")
        
        if "appearance" not in base_char:
            base_char["appearance"] = {}
        
        all_descriptions = []
        all_personalities = []
        
        for occ in occurrences:
            if not isinstance(occ, dict):
                logger.warning(f"Skipping non-dict occurrence in character merge")
                continue
            
            if occ.get("description"):
                all_descriptions.append(occ["description"])
            
            if occ.get("personality"):
                all_personalities.append(occ["personality"])
            
            try:
                for key, value in occ.get("appearance", {}).items():
                    if value and (not base_char["appearance"].get(key) or 
                                len(str(value)) > len(str(base_char["appearance"].get(key, "")))):
                        base_char["appearance"][key] = value
            except (AttributeError, TypeError) as e:
                logger.warning(f"Error merging appearance data: {e}")
        
        if all_descriptions:
            base_char["description"] = " ".join(set(all_descriptions))
        if all_personalities:
            base_char["personality"] = ", ".join(set(all_personalities))
        
        return base_char
    
    def _validate_input(self, novel_text: str):
        if not novel_text or len(novel_text.strip()) < self.config.min_text_length:
            raise ValidationError(
                f"Novel text too short. Minimum {self.config.min_text_length} characters required"
            )
        
        if len(novel_text) > self.config.max_text_length:
            raise ValidationError(
                f"Novel text too long. Maximum {self.config.max_text_length} characters allowed"
            )
    
    def _build_variables(
        self,
        novel_text: str,
    ) -> Dict[str, Any]:
        """Build LangChain prompt variables dictionary"""
        return {
            "novel_text": novel_text,
            "max_characters": self.config.max_characters,
            "max_scenes": self.config.max_scenes,
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
    ) -> Dict[str, Any]:
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
