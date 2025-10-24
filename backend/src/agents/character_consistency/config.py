from pydantic import BaseModel, Field


class CharacterConsistencyConfig(BaseModel):
    temperature: float = Field(default=0.7, description="Temperature for image generation prompt")
    storage_base_path: str = Field(default="data/characters", description="Base path for character storage")
    reference_image_prompt_suffix: str = Field(
        default="full body portrait, white background, no environment, clear features, anime style, high quality",
        description="Suffix for reference image generation prompt"
    )
    enable_caching: bool = Field(default=True, description="Enable character template caching")
