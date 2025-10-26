from pydantic import BaseModel, Field


class NovelParserConfig(BaseModel):
    max_characters: int = Field(default=10, description="Maximum number of characters to extract")
    max_scenes: int = Field(default=30, description="Maximum number of scenes to extract")
    temperature: float = Field(default=0.3, description="Temperature for LLM")
    min_text_length: int = Field(default=100, description="Minimum text length")
    max_text_length: int = Field(default=50000, description="Maximum text length")
    auto_chunk_threshold: int = Field(default=10000, description="Automatically chunk text if length exceeds this threshold")
    chunk_size: int = Field(default=4000, description="Size of each chunk when splitting text")