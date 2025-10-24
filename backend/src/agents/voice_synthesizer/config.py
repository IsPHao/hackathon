from pydantic import BaseModel, Field


class VoiceSynthesizerConfig(BaseModel):
    model: str = Field(default="tts-1", description="TTS model to use")
    speed: float = Field(default=1.0, ge=0.25, le=4.0, description="Speech speed")
    voice_mapping: dict = Field(
        default_factory=lambda: {
            "male_young": "alloy",
            "male_adult": "onyx",
            "female_young": "nova",
            "female_adult": "shimmer",
            "narrator": "fable"
        },
        description="Character type to voice mapping"
    )
    audio_format: str = Field(default="mp3", description="Output audio format")
    enable_post_processing: bool = Field(default=True, description="Enable audio post-processing")
    fade_duration: int = Field(default=100, ge=0, description="Fade in/out duration in milliseconds")
    max_text_length: int = Field(default=4096, description="Maximum text length for TTS")
