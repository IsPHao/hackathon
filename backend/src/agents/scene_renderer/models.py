from typing import List, Dict, Any
from pydantic import BaseModel, Field


class RenderedScene(BaseModel):
    scene_id: int = Field(..., description="场景编号")
    chapter_id: int = Field(..., description="所属章节编号")
    image_path: str = Field(..., description="图片文件路径")
    audio_path: str = Field(..., description="音频文件路径")
    duration: float = Field(..., description="实际时长（秒）")
    audio_duration: float = Field(default=0.0, description="音频时长（秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外的元数据")


class RenderedChapter(BaseModel):
    chapter_id: int = Field(..., description="章节编号")
    title: str = Field(default="", description="章节标题")
    scenes: List[RenderedScene] = Field(default_factory=list, description="渲染后的场景列表")
    total_duration: float = Field(default=0.0, description="章节总时长（秒）")


class RenderResult(BaseModel):
    chapters: List[RenderedChapter] = Field(default_factory=list, description="渲染后的章节列表")
    total_duration: float = Field(default=0.0, description="总时长（秒）")
    total_scenes: int = Field(default=0, description="总场景数量")
    output_directory: str = Field(..., description="输出目录路径")
