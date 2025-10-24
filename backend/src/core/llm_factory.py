from typing import Dict, Any, Optional, Literal
import os
from enum import Enum

from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI


class LLMCapability(Enum):
    JSON_MODE = "json_mode"
    IMAGE_GENERATION = "image_generation"
    AUDIO_GENERATION = "audio_generation"
    TEXT_GENERATION = "text_generation"


class LLMType(Enum):
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"
    GPT35_TURBO = "gpt-3.5-turbo"


LLM_CAPABILITIES: Dict[LLMType, list[LLMCapability]] = {
    LLMType.GPT4O: [
        LLMCapability.JSON_MODE,
        LLMCapability.TEXT_GENERATION,
    ],
    LLMType.GPT4O_MINI: [
        LLMCapability.JSON_MODE,
        LLMCapability.TEXT_GENERATION,
    ],
    LLMType.GPT35_TURBO: [
        LLMCapability.JSON_MODE,
        LLMCapability.TEXT_GENERATION,
    ],
}


AGENT_LLM_MAPPING: Dict[str, LLMType] = {
    "novel_parser": LLMType.GPT4O_MINI,
    "storyboard": LLMType.GPT4O_MINI,
    "character_consistency": LLMType.GPT4O,
}


class LLMFactory:
    
    @staticmethod
    def create_chat_llm(
        agent_name: str,
        temperature: float = 0.3,
        api_key: Optional[str] = None
    ) -> ChatOpenAI:
        llm_type = AGENT_LLM_MAPPING.get(agent_name, LLMType.GPT4O_MINI)
        
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        return ChatOpenAI(
            model=llm_type.value,
            temperature=temperature,
            api_key=api_key,
        )
    
    @staticmethod
    def create_openai_client(api_key: Optional[str] = None) -> AsyncOpenAI:
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        return AsyncOpenAI(api_key=api_key)
    
    @staticmethod
    def get_recommended_model(
        capability: LLMCapability,
        prefer_fast: bool = True
    ) -> LLMType:
        candidates = [
            llm_type for llm_type, caps in LLM_CAPABILITIES.items()
            if capability in caps
        ]
        
        if not candidates:
            return LLMType.GPT4O_MINI
        
        if prefer_fast:
            if LLMType.GPT4O_MINI in candidates:
                return LLMType.GPT4O_MINI
            if LLMType.GPT35_TURBO in candidates:
                return LLMType.GPT35_TURBO
        
        return candidates[0]
    
    @staticmethod
    def supports_capability(llm_type: LLMType, capability: LLMCapability) -> bool:
        return capability in LLM_CAPABILITIES.get(llm_type, [])
