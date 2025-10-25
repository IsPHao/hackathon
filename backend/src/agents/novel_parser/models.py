from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError


class CharacterAppearance(BaseModel):
    gender: str = Field(description="Character gender (male/female)")
    age: int = Field(description="Character age")
    hair: str = Field(description="Hair style and color")
    eyes: str = Field(description="Eye color and features")
    clothing: str = Field(description="Typical clothing")
    features: str = Field(description="Unique features")


class VisualDescription(BaseModel):
    prompt: str = Field(description="Image generation prompt")
    negative_prompt: str = Field(description="Negative prompt for image generation")
    style_tags: List[str] = Field(default_factory=list, description="Style tags")


class Character(BaseModel):
    name: str = Field(description="Character name")
    description: str = Field(description="Character description")
    appearance: CharacterAppearance = Field(description="Character appearance details")
    personality: str = Field(description="Character personality traits")
    visual_description: Optional[VisualDescription] = Field(
        default=None, description="Enhanced visual description for image generation"
    )


class Dialogue(BaseModel):
    character: str = Field(description="Character name")
    text: str = Field(description="Dialogue text")


class Scene(BaseModel):
    scene_id: int = Field(description="Scene ID")
    location: str = Field(description="Scene location")
    time: str = Field(description="Scene time")
    characters: List[str] = Field(default_factory=list, description="Characters in scene")
    description: str = Field(description="Scene description")
    dialogue: List[Dialogue] = Field(default_factory=list, description="Dialogue in scene")
    actions: List[str] = Field(default_factory=list, description="Actions in scene")
    atmosphere: str = Field(description="Scene atmosphere")


class PlotPoint(BaseModel):
    scene_id: int = Field(description="Scene ID")
    type: str = Field(description="Plot point type (conflict/climax/resolution)")
    description: str = Field(description="Plot point description")


class NovelData(BaseModel):
    """
    Complete novel data structure containing all information needed for anime generation
    """
    characters: List[Character] = Field(description="List of characters")
    scenes: List[Scene] = Field(description="List of scenes")
    plot_points: List[PlotPoint] = Field(description="List of plot points")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        try:
            return self.model_dump()
        except Exception as e:
            raise ValueError(f"Failed to convert NovelData to dictionary: {e}") from e
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NovelData":
        """
        Create from dictionary
        
        Args:
            data: Dictionary containing novel data
        
        Returns:
            NovelData: Validated NovelData instance
        
        Raises:
            ValueError: If validation fails
        """
        if not isinstance(data, dict):
            raise ValueError(f"Expected dictionary, got {type(data).__name__}")
        
        try:
            return cls.model_validate(data)
        except PydanticValidationError as e:
            error_details = []
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                error_details.append(f"{field}: {msg}")
            raise ValueError(
                f"NovelData validation failed:\n" + "\n".join(error_details)
            ) from e
        except Exception as e:
            raise ValueError(f"Failed to create NovelData from dictionary: {e}") from e
