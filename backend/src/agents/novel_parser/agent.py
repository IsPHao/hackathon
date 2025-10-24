from typing import Dict, List, Any, Optional
import json
import logging
from collections import defaultdict

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from .config import NovelParserConfig
from .exceptions import ValidationError, ParseError, APIError
from .prompts import (
    NOVEL_PARSE_PROMPT,
    CHARACTER_APPEARANCE_ENHANCE_PROMPT,
)

logger = logging.getLogger(__name__)


class NovelParserAgent:
    
    def __init__(
        self,
        llm: ChatOpenAI,
        config: Optional[NovelParserConfig] = None,
    ):
        self.config = config or NovelParserConfig()
        self.llm = llm
    
    async def parse(
        self,
        novel_text: str,
        mode: str = "enhanced",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._validate_input(novel_text)
        
        if mode not in ["enhanced", "simple"]:
            raise ValidationError(f"Invalid mode: {mode}. Must be 'enhanced' or 'simple'")
        
        if mode == "enhanced":
            result = await self._parse_enhanced(novel_text, options)
        else:
            result = await self._parse_simple(novel_text, options)
        
        self._validate_output(result)
        
        return result
    
    async def _parse_simple(
        self,
        novel_text: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(novel_text, options)
        parsed_data = await self._call_llm_json(prompt)
        
        if self.config.enable_character_enhancement:
            parsed_data["characters"] = await self._enhance_characters(
                parsed_data["characters"]
            )
        
        return parsed_data
    
    async def _parse_enhanced(
        self,
        novel_text: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        chunk_size = 5000
        chunks = self._split_text_into_chunks(novel_text, chunk_size)
        
        logger.info(f"Split novel into {len(chunks)} chunks for enhanced parsing")
        
        chunk_results = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            prompt = self._build_prompt(chunk, options)
            parsed_chunk = await self._call_llm_json(prompt)
            chunk_results.append(parsed_chunk)
        
        merged_result = self._merge_results(chunk_results)
        
        if self.config.enable_character_enhancement:
            merged_result["characters"] = await self._enhance_characters(
                merged_result["characters"]
            )
        
        return merged_result
    
    def _split_text_into_chunks(self, text: str, chunk_size: int) -> List[str]:
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
                scene_offset = all_scenes[-1]["scene_id"]
        
        merged_characters = []
        for name, occurrences in character_map.items():
            if len(occurrences) == 1:
                merged_characters.append(occurrences[0])
            else:
                merged_char = self._merge_character_occurrences(occurrences)
                merged_characters.append(merged_char)
        
        return {
            "characters": merged_characters[:self.config.max_characters],
            "scenes": all_scenes[:self.config.max_scenes],
            "plot_points": all_plot_points,
        }
    
    def _merge_character_occurrences(
        self, occurrences: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        base_char = occurrences[0].copy()
        
        all_descriptions = []
        all_personalities = []
        
        for occ in occurrences:
            if occ.get("description"):
                all_descriptions.append(occ["description"])
            if occ.get("personality"):
                all_personalities.append(occ["personality"])
            
            if "appearance" in occ and occ["appearance"]:
                for key, value in occ["appearance"].items():
                    if value and (not base_char.get("appearance", {}).get(key) or 
                                  len(str(value)) > len(str(base_char["appearance"].get(key, "")))):
                        if "appearance" not in base_char:
                            base_char["appearance"] = {}
                        base_char["appearance"][key] = value
        
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
    
    def _build_prompt(
        self,
        novel_text: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        max_characters = self.config.max_characters
        max_scenes = self.config.max_scenes
        
        if options:
            max_characters = options.get("max_characters", max_characters)
            max_scenes = options.get("max_scenes", max_scenes)
        
        return NOVEL_PARSE_PROMPT.format(
            novel_text=novel_text,
            max_characters=max_characters,
            max_scenes=max_scenes,
        )
    
    async def _call_llm_json(self, prompt: str) -> Dict[str, Any]:
        try:
            messages = [
                ("system", "You are a professional novel analysis expert."),
                ("human", prompt),
            ]
            
            response = await self.llm.ainvoke(
                messages,
                response_format={"type": "json_object"},
            )
            
            return json.loads(response.content)
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ParseError(f"Invalid JSON response: {e}") from e
        
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise APIError(f"Failed to call LLM API: {e}") from e
    
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
    ) -> Dict[str, str]:
        prompt = CHARACTER_APPEARANCE_ENHANCE_PROMPT.format(
            name=character.get("name", "Unknown"),
            description=character.get("description", ""),
            appearance=json.dumps(character.get("appearance", {}), ensure_ascii=False),
        )
        
        try:
            response = await self._call_llm_json(prompt)
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