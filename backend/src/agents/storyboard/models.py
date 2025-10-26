from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CharacterRenderInfo(BaseModel):
    name: str = Field(..., description="角色名称")
    gender: str = Field(default="unknown", description="角色性别")
    age: Optional[int] = Field(default=None, description="角色年龄")
    age_stage: str = Field(default="", description="年龄段描述")
    hair: str = Field(default="", description="发型和颜色")
    eyes: str = Field(default="", description="眼睛颜色和特征")
    clothing: str = Field(default="", description="典型服装")
    features: str = Field(default="", description="独特特征")
    body_type: str = Field(default="", description="体型特征")
    height: str = Field(default="", description="身高描述")
    skin: str = Field(default="", description="肤色特征")
    personality: str = Field(default="", description="性格特点")
    role: str = Field(default="", description="在故事中的作用")


class AudioInfo(BaseModel):
    type: str = Field(..., description="音频类型：narration(旁白) 或 dialogue(对话)")
    speaker: str = Field(default="", description="说话者（旁白时为空或'narrator'）")
    text: str = Field(default="", description="文本内容")
    estimated_duration: float = Field(default=0.0, description="预估时长（秒）")


class ImageRenderInfo(BaseModel):
    prompt: str = Field(default="", description="图像生成正向提示词")
    negative_prompt: str = Field(default="low quality, blurry", description="图像生成负向提示词")
    style_tags: List[str] = Field(default_factory=lambda: ["anime"], description="风格标签")
    shot_type: str = Field(default="medium_shot", description="镜头类型")
    camera_angle: str = Field(default="eye_level", description="镜头角度")
    composition: str = Field(default="centered", description="构图原则")
    lighting: str = Field(default="natural", description="光线设计")


class StoryboardScene(BaseModel):
    scene_id: int = Field(..., description="场景编号")
    chapter_id: int = Field(..., description="所属章节编号")
    
    location: str = Field(default="", description="地点")
    time: str = Field(default="", description="时间")
    atmosphere: str = Field(default="", description="氛围")
    description: str = Field(default="", description="场景描述")
    
    characters: List[CharacterRenderInfo] = Field(
        default_factory=list,
        description="当前场景中的角色完整渲染信息"
    )
    
    audio: AudioInfo = Field(..., description="音频信息（对白或旁白）")
    
    image: ImageRenderInfo = Field(
        default_factory=ImageRenderInfo,
        description="图像渲染信息"
    )
    
    duration: float = Field(default=3.0, description="分镜时长（秒）")
    
    character_action: str = Field(default="", description="角色当前动作描述")


class StoryboardChapter(BaseModel):
    chapter_id: int = Field(..., description="章节编号")
    title: str = Field(default="", description="章节标题")
    summary: str = Field(default="", description="章节概要")
    scenes: List[StoryboardScene] = Field(default_factory=list, description="章节包含的分镜列表")


class StoryboardResult(BaseModel):
    chapters: List[StoryboardChapter] = Field(default_factory=list, description="章节列表")
    total_duration: float = Field(default=0.0, description="总时长（秒）")
    total_scenes: int = Field(default=0, description="总分镜数量")
