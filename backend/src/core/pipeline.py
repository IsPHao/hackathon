from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
import asyncio
import logging

from langchain_openai import ChatOpenAI

from ..agents.novel_parser import NovelParserAgent, NovelParserConfig
from ..agents.storyboard import StoryboardAgent, StoryboardConfig
from ..agents.character_consistency import CharacterConsistencyAgent, CharacterConsistencyConfig
from ..agents.image_generator import ImageGeneratorAgent, ImageGeneratorConfig
from ..agents.voice_synthesizer import VoiceSynthesizerAgent, VoiceSynthesizerConfig
from ..agents.video_composer import VideoComposerAgent, VideoComposerConfig

logger = logging.getLogger(__name__)

class AnimePipeline:
    """
    动漫生成主工作流编排器
    
    负责协调各个Agent的执行顺序，管理Agent之间的数据流转，
    处理工作流级别的错误，并上报整体进度。
    """
    
    def __init__(self):
        # Initialize LLM
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        
        # Initialize agents with their configs
        self.novel_parser = NovelParserAgent(
            llm=self.llm,
            config=NovelParserConfig()
        )
        
        self.storyboard = StoryboardAgent(
            llm=self.llm,
            config=StoryboardConfig()
        )
        
        self.character_consistency = CharacterConsistencyAgent(
            llm=self.llm,
            config=CharacterConsistencyConfig()
        )
        
        task_id = str(uuid4())
        
        self.image_generator = ImageGeneratorAgent(
            task_id=task_id,
            config=ImageGeneratorConfig()
        )
        
        self.voice_synthesizer = VoiceSynthesizerAgent(
            task_id=task_id,
            config=VoiceSynthesizerConfig()
        )
        
        self.video_composer = VideoComposerAgent(
            task_id=task_id,
            config=VideoComposerConfig()
        )
    
    async def execute(
        self,
        novel_text: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行完整的动漫生成流程
        
        按照以下顺序执行各个Agent：
        1. 小说解析
        2. 分镜设计
        3. 角色一致性管理
        4. 并行生成图片和音频
        5. 视频合成
        
        Args:
            novel_text: 待处理的小说文本
            options: 可选配置参数，如风格、质量等
        
        Returns:
            Dict[str, Any]: 包含以下键的字典：
                - video_path: 生成的视频路径
                - scenes_count: 场景数量
        """
        print("开始执行动漫生成流程...")
        
        # 1. 小说解析
        print("1. 开始解析小说...")
        novel_data = await self.novel_parser.execute(novel_text)
        print("小说解析完成")
        
        # 2. 分镜设计
        print("2. 开始分镜设计...")
        storyboard_data = await self.storyboard.execute(novel_data)
        print("分镜设计完成")
        
        # 3. 角色一致性管理
        print("3. 管理角色一致性...")
        project_id = str(uuid4())
        character_data = await self.character_consistency.execute(
            novel_data.get("characters", []), 
            project_id
        )
        print("角色管理完成")
        
        # 4. 并行生成图片和音频
        print("4. 开始生成图片和音频...")
        scenes = storyboard_data.get("scenes", [])
        
        # 生成图片和音频的任务
        image_tasks = []
        audio_tasks = []
        
        for i, scene in enumerate(scenes):
            # 为每个场景创建图像生成任务
            image_task = self.image_generator.execute(
                scene=scene,
                character_templates=character_data
            )
            image_tasks.append(image_task)
            
            # 为每个场景创建音频生成任务
            # 获取场景中的对话文本
            dialogue_text = ""
            if "image_prompt" in scene:
                dialogue_text = scene.get("image_prompt", "")[:200]  # 限制长度
            
            audio_task = self.voice_synthesizer.execute(
                text=dialogue_text if dialogue_text else "在这个场景中，一切都很安静。",
                character=None,
                character_info=None
            )
            audio_tasks.append(audio_task)
        
        # 并行执行所有图像和音频生成任务
        images = await asyncio.gather(*image_tasks)
        audios = await asyncio.gather(*audio_tasks)
        print("图片和音频生成完成")
        
        # 5. 视频合成
        print("5. 开始合成视频...")
        video_result = await self.video_composer.execute(images, audios, storyboard_data)
        print("视频合成完成")
        
        return {
            "video_path": video_result.get("url", ""),
            "scenes_count": len(scenes)
        }
    
    
