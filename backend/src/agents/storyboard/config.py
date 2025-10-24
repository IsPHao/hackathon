from pydantic import BaseModel, Field


class StoryboardConfig(BaseModel):
    max_scenes: int = Field(default=30, description="Maximum number of scenes to process")
    min_scene_duration: float = Field(default=3.0, description="Minimum scene duration in seconds")
    max_scene_duration: float = Field(default=10.0, description="Maximum scene duration in seconds")
    dialogue_chars_per_second: float = Field(default=3.0, description="Characters per second for dialogue")
    action_duration: float = Field(default=1.5, description="Duration per action in seconds")
    temperature: float = Field(default=0.7, description="Temperature for LLM")
