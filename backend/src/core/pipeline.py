from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
import asyncio
import logging
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from langchain_openai import ChatOpenAI

from agents.novel_parser import NovelParserAgent, NovelParserConfig
from agents.storyboard import StoryboardAgent, StoryboardConfig
from agents.scene_renderer import SceneRenderer, SceneRendererConfig
from agents.scene_composer import SceneComposer, SceneComposerConfig

from .progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

class AnimePipeline:
    """
    动漫生成主工作流编排器
    
    负责协调各个Agent的执行顺序，管理Agent之间的数据流转，
    处理工作流级别的错误，并上报整体进度。
    
    新的流程:
    1. NovelParserAgent: 解析小说文本
    2. StoryboardAgent: 生成分镜脚本
    3. SceneRenderer: 渲染场景（生成图片和音频）
    4. SceneComposer: 合成视频
    """
    
    def __init__(self, api_key, progress_tracker, task_id):
        self.id = task_id
        
        self.llm = ChatOpenAI(
            model="claude-3.5-sonnet",
            api_key=api_key,
            base_url="https://openai.qiniu.com/v1",
            timeout=180
        )
        
        self.novel_parser = NovelParserAgent(
            llm=self.llm,
            config=NovelParserConfig()
        )
        
        self.storyboard = StoryboardAgent(
            llm=self.llm,
            config=StoryboardConfig()
        )
        
        self.scene_renderer = SceneRenderer(
            task_id=str(self.id),
            config=SceneRendererConfig(
                qiniu_api_key=api_key
            )
        )
        
        self.scene_composer = SceneComposer(
            task_id=str(self.id),
            config=SceneComposerConfig()
        )

        self.progress_tracker = progress_tracker
    
    async def execute(
        self,
        novel_text: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行完整的动漫生成流程
        
        新的执行流程：
        1. 小说解析 (NovelParserAgent)
        2. 分镜设计 (StoryboardAgent)
        3. 场景渲染 (SceneRenderer) - 生成图片和音频
        4. 视频合成 (SceneComposer) - 合成最终视频
        
        Args:
            novel_text: 待处理的小说文本
            options: 可选配置参数
        
        Returns:
            Dict[str, Any]: 包含以下键的字典：
                - video_path: 生成的视频路径
                - duration: 视频时长
                - scenes_count: 场景数量
        """
        logger.info("开始执行动漫生成流程...")
        await self.progress_tracker.update(self.id, "开始执行", 1, "开始执行")

        logger.info("1. 开始解析小说...")
        await self.progress_tracker.update(self.id, "小说解析中", 10, "小说解析中")
        novel_result = await self.novel_parser.parse(novel_text)
        await self.progress_tracker.update(self.id, "小说解析完成", 20, "小说解析完成")
        logger.info("小说解析完成")
        
        logger.info("2. 开始分镜设计...")
        await self.progress_tracker.update(self.id, "分镜设计中", 25, "分镜设计中")
        novel_data_dict = novel_result.model_dump()
        storyboard_data = await self.storyboard.create(novel_data_dict)
        await self.progress_tracker.update(self.id, "分镜设计完成", 30, "分镜设计完成")
        logger.info("分镜设计完成")
        
        logger.info("3. 开始渲染场景（生成图片和音频）...")
        await self.progress_tracker.update(self.id, "场景渲染中", 40, "场景渲染中")
        from agents.storyboard.models import StoryboardResult
        storyboard_result = StoryboardResult(**storyboard_data)
        logger.info(f"场景渲染数据: {storyboard_result.model_dump()}")
        render_result = await self.scene_renderer.render(storyboard_result)
        await self.progress_tracker.update(self.id, "场景渲染完成", 70, "场景渲染完成")
        logger.info(f"场景渲染完成: {render_result.total_scenes} 个场景")
        
        logger.info("4. 开始合成视频...")
        await self.progress_tracker.update(self.id, "视频合成中", 80, "视频合成中")
        video_result = await self.scene_composer.compose(render_result)
        await self.progress_tracker.update(self.id, "视频合成完成", 100, "视频合成完成")
        logger.info(f"视频合成完成: {video_result['video_path']}")
        
        await self.progress_tracker.complete(self.id, video_result["video_path"])
        
        return {
            "video_path": video_result["video_path"],
            "duration": video_result.get("duration", 0.0),
            "scenes_count": render_result.total_scenes
        }
    
