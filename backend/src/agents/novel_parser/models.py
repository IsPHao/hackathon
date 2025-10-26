from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CharacterAppearance(BaseModel):
    gender: str = Field(default="unknown", description="角色性别")
    age: Optional[int] = Field(default=None, description="角色年龄")
    age_stage: str = Field(default="", description="年龄段描述，如：童年、少年、青年、中年、老年")
    hair: str = Field(default="", description="发型和颜色")
    eyes: str = Field(default="", description="眼睛颜色和特征")
    clothing: str = Field(default="", description="典型服装")
    features: str = Field(default="", description="独特特征")
    body_type: str = Field(default="", description="体型特征")
    height: str = Field(default="", description="身高描述")
    skin: str = Field(default="", description="肤色特征")


class VisualDescription(BaseModel):
    prompt: str = Field(default="", description="图像生成正向提示词")
    negative_prompt: str = Field(default="low quality, blurry", description="图像生成负向提示词")
    style_tags: List[str] = Field(default_factory=lambda: ["anime"], description="风格标签")


class CharacterInfo(BaseModel):
    name: str = Field(..., description="角色名称")
    description: str = Field(default="", description="角色简短描述")
    appearance: CharacterAppearance = Field(default_factory=CharacterAppearance, description="外貌信息")
    personality: str = Field(default="", description="性格特点")
    role: str = Field(default="", description="在故事中的作用")
    visual_description: Optional[VisualDescription] = Field(default=None, description="视觉化描述（用于生图）")
    age_variants: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="不同年龄段的外貌信息变化，格式：[{'age_stage': '童年', 'appearance': {...}, 'visual_description': {...}}]"
    )


class Dialogue(BaseModel):
    character: str = Field(default="旁白", description="说话角色")
    text: str = Field(default="", description="对话内容")


class SceneInfo(BaseModel):
    scene_id: int = Field(..., description="场景编号")
    location: str = Field(default="", description="地点")
    time: str = Field(default="", description="时间")
    characters: List[str] = Field(default_factory=list, description="出现的角色")
    description: str = Field(default="", description="场景环境描述")
    narration: str = Field(default="", description="旁白描述")
    dialogue: List[Dialogue] = Field(default_factory=list, description="对话内容")
    actions: List[str] = Field(default_factory=list, description="动作描述")
    atmosphere: str = Field(default="", description="氛围")
    lighting: str = Field(default="", description="光线描述")
    character_appearances: Dict[str, CharacterAppearance] = Field(
        default_factory=dict,
        description="本场景中角色的外貌更新（如果有描述）"
    )


class PlotPoint(BaseModel):
    scene_id: int = Field(..., description="关联的场景编号")
    type: str = Field(default="normal", description="情节类型：conflict/climax/resolution/normal")
    description: str = Field(default="", description="情节描述")


class NovelParseResult(BaseModel):
    characters: List[CharacterInfo] = Field(default_factory=list, description="角色列表")
    scenes: List[SceneInfo] = Field(default_factory=list, description="场景列表")
    plot_points: List[PlotPoint] = Field(default_factory=list, description="情节点列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "characters": [
                    {
                        "name": "小明",
                        "description": "一个16岁的高中生",
                        "appearance": {
                            "gender": "male",
                            "age": 16,
                            "age_stage": "少年",
                            "hair": "短黑发",
                            "eyes": "棕色眼睛",
                            "clothing": "校服",
                            "features": "阳光笑容"
                        },
                        "personality": "开朗、热情、勇敢"
                    }
                ],
                "scenes": [
                    {
                        "scene_id": 1,
                        "location": "学校教室",
                        "time": "早晨",
                        "characters": ["小明"],
                        "description": "阳光透过窗户洒进教室",
                        "dialogue": [
                            {"character": "小明", "text": "今天天气真好"}
                        ]
                    }
                ],
                "plot_points": [
                    {
                        "scene_id": 1,
                        "type": "normal",
                        "description": "故事开始"
                    }
                ]
            }
        }
