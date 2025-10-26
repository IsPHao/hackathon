from typing import Dict, List, Any, Optional
import logging
import copy
from collections import defaultdict

from langchain_openai import ChatOpenAI
from pydantic import ValidationError as PydanticValidationError

from .config import NovelParserConfig
from .models import (
    NovelParseResult,
    CharacterInfo,
    CharacterAppearance,
    SceneInfo,
    PlotPoint,
    VisualDescription,
    Dialogue,
    Chapter,
)
from ..base.exceptions import ValidationError, ParseError, APIError
from .prompts import NOVEL_PARSE_PROMPT_TEMPLATE
from ..base.llm_utils import call_llm_json

logger = logging.getLogger(__name__)


class NovelParserAgent:
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
        self.config = config or NovelParserConfig()
        self.llm = llm
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def parse(
        self,
        novel_text: str,
        mode: str = "enhanced",
        options: Optional[Dict[str, Any]] = None,
    ) -> NovelParseResult:
        """
        解析小说文本
        
        Args:
            novel_text: 小说原文
            mode: 解析模式，'simple'或'enhanced'
            options: 额外配置选项
        
        Returns:
            NovelParseResult: 结构化的解析结果
        
        Raises:
            ValidationError: 输入验证失败
            ParseError: 解析失败
        """
        self._validate_input(novel_text)
        
        if mode not in ["enhanced", "simple"]:
            raise ValidationError(f"Invalid mode: {mode}. Must be 'enhanced' or 'simple'")
        
        if mode == "enhanced":
            result_dict = await self._parse_enhanced(novel_text, options)
        else:
            result_dict = await self._parse_simple(novel_text, options)
        
        # 转换为Pydantic模型
        try:
            result = self._convert_to_model(result_dict)
        except Exception as e:
            logger.error(f"Failed to convert to Pydantic model: {e}")
            result = self._create_safe_model(result_dict)
        
        self._validate_output_model(result)
        
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
    
    def _split_text_into_chunks(self, text: str) -> List[str]:
        config: NovelParserConfig = self.config  # type: ignore
        chunk_size = config.chunk_size
        
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
        all_chapters = []
        all_plot_points = []
        
        scene_offset = 0
        chapter_offset = 0
        
        for chunk_result in chunk_results:
            for char in chunk_result.get("characters", []):
                character_map[char["name"]].append(char)
            
            for chapter in chunk_result.get("chapters", []):
                chapter["chapter_id"] += chapter_offset
                
                for scene in chapter.get("scenes", []):
                    scene["scene_id"] += scene_offset
                    scene_offset += 1
                
                all_chapters.append(chapter)
            
            for plot_point in chunk_result.get("plot_points", []):
                plot_point["scene_id"] += scene_offset
                all_plot_points.append(plot_point)
            
            if chunk_result.get("chapters"):
                chapter_offset += len(chunk_result["chapters"])
        
        merged_characters = []
        for name, occurrences in character_map.items():
            if len(occurrences) == 1:
                merged_characters.append(occurrences[0])
            else:
                merged_char = self._merge_character_occurrences(occurrences)
                merged_characters.append(merged_char)
        
        return {
            "characters": merged_characters,
            "chapters": all_chapters,
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
    
    
    def _convert_to_model(self, data: Dict[str, Any]) -> NovelParseResult:
        try:
            characters = []
            for char_data in data.get("characters", []):
                appearance_data = char_data.get("appearance", {})
                appearance = CharacterAppearance(**appearance_data)
                
                visual_desc = None
                if char_data.get("visual_description"):
                    visual_desc = VisualDescription(**char_data["visual_description"])
                
                age_variants = char_data.get("age_variants", [])
                
                character = CharacterInfo(
                    name=char_data.get("name", "Unknown"),
                    description=char_data.get("description", ""),
                    appearance=appearance,
                    personality=char_data.get("personality", ""),
                    role=char_data.get("role", ""),
                    visual_description=visual_desc,
                    age_variants=age_variants,
                )
                characters.append(character)
            
            chapters = []
            for chapter_data in data.get("chapters", []):
                scenes = []
                for scene_data in chapter_data.get("scenes", []):
                    dialogue_list = []
                    for dlg in scene_data.get("dialogue", []):
                        dialogue_list.append(Dialogue(**dlg))
                    
                    char_appearances = {}
                    for char_name, app_data in scene_data.get("character_appearances", {}).items():
                        char_appearances[char_name] = CharacterAppearance(**app_data)
                    
                    scene = SceneInfo(
                        scene_id=scene_data.get("scene_id", 0),
                        location=scene_data.get("location", ""),
                        time=scene_data.get("time", ""),
                        characters=scene_data.get("characters", []),
                        description=scene_data.get("description", ""),
                        narration=scene_data.get("narration", ""),
                        dialogue=dialogue_list,
                        actions=scene_data.get("actions", []),
                        atmosphere=scene_data.get("atmosphere", ""),
                        lighting=scene_data.get("lighting", ""),
                        character_appearances=char_appearances,
                    )
                    scenes.append(scene)
                
                chapter = Chapter(
                    chapter_id=chapter_data.get("chapter_id", len(chapters) + 1),
                    title=chapter_data.get("title", ""),
                    summary=chapter_data.get("summary", ""),
                    scenes=scenes,
                )
                chapters.append(chapter)
            
            plot_points = []
            for pp_data in data.get("plot_points", []):
                plot_point = PlotPoint(**pp_data)
                plot_points.append(plot_point)
            
            return NovelParseResult(
                characters=characters,
                chapters=chapters,
                plot_points=plot_points,
            )
        except PydanticValidationError as e:
            logger.error(f"Pydantic validation error: {e}")
            raise ParseError(f"Failed to validate parsed data: {e}") from e
    
    def _create_safe_model(self, data: Dict[str, Any]) -> NovelParseResult:
        try:
            characters = []
            for char_data in data.get("characters", []):
                try:
                    appearance = CharacterAppearance()
                    if isinstance(char_data.get("appearance"), dict):
                        appearance = CharacterAppearance(**char_data["appearance"])
                    
                    character = CharacterInfo(
                        name=char_data.get("name", "Unknown"),
                        description=char_data.get("description", ""),
                        appearance=appearance,
                        personality=char_data.get("personality", ""),
                        role=char_data.get("role", ""),
                    )
                    characters.append(character)
                except Exception as e:
                    logger.warning(f"Skipping invalid character: {e}")
                    continue
            
            chapters = []
            for chapter_data in data.get("chapters", []):
                try:
                    scenes = []
                    for scene_data in chapter_data.get("scenes", []):
                        try:
                            dialogue_list = []
                            for dlg in scene_data.get("dialogue", []):
                                try:
                                    dialogue_list.append(Dialogue(**dlg))
                                except:
                                    continue
                            
                            scene = SceneInfo(
                                scene_id=scene_data.get("scene_id", len(scenes)),
                                location=scene_data.get("location", ""),
                                time=scene_data.get("time", ""),
                                characters=scene_data.get("characters", []),
                                description=scene_data.get("description", ""),
                                narration=scene_data.get("narration", ""),
                                dialogue=dialogue_list,
                                actions=scene_data.get("actions", []),
                                atmosphere=scene_data.get("atmosphere", ""),
                            )
                            scenes.append(scene)
                        except Exception as e:
                            logger.warning(f"Skipping invalid scene: {e}")
                            continue
                    
                    chapter = Chapter(
                        chapter_id=chapter_data.get("chapter_id", len(chapters) + 1),
                        title=chapter_data.get("title", ""),
                        summary=chapter_data.get("summary", ""),
                        scenes=scenes,
                    )
                    chapters.append(chapter)
                except Exception as e:
                    logger.warning(f"Skipping invalid chapter: {e}")
                    continue
            
            plot_points = []
            for pp_data in data.get("plot_points", []):
                try:
                    plot_point = PlotPoint(**pp_data)
                    plot_points.append(plot_point)
                except:
                    continue
            
            return NovelParseResult(
                characters=characters,
                chapters=chapters,
                plot_points=plot_points,
            )
        except Exception as e:
            logger.error(f"Failed to create safe model: {e}")
            return NovelParseResult(
                characters=[],
                chapters=[],
                plot_points=[],
            )
    
    def _validate_output_model(self, result: NovelParseResult):
        if not result.characters:
            raise ValidationError("No characters extracted")
        
        if not result.chapters:
            raise ValidationError("No chapters extracted")