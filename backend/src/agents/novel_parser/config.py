from pydantic import BaseModel, Field


class NovelParserConfig(BaseModel):
    max_characters: int = Field(default=10, description="Maximum number of characters to extract")
    max_scenes: int = Field(default=30, description="Maximum number of scenes to extract")
    temperature: float = Field(default=0.3, description="Temperature for LLM")
    enable_character_enhancement: bool = Field(default=True, description="Enable enhanced character recognition")
    min_text_length: int = Field(default=100, description="Minimum text length")
    max_text_length: int = Field(default=50000, description="Maximum text length")