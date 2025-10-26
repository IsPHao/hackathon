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
from agents.character_consistency import CharacterConsistencyAgent, CharacterConsistencyConfig
from agents.image_generator import ImageGeneratorAgent, ImageGeneratorConfig
from agents.voice_synthesizer import VoiceSynthesizerAgent, VoiceSynthesizerConfig
from agents.video_composer import VideoComposerAgent, VideoComposerConfig

from .progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

class AnimePipeline:
    """
    动漫生成主工作流编排器
    
    负责协调各个Agent的执行顺序，管理Agent之间的数据流转，
    处理工作流级别的错误，并上报整体进度。
    """
    
    def __init__(self, api_key, progress_tracker, task_id):
        # id
        self.id = task_id
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="claude-3.5-sonnet",
            # model="claude-4.5-sonnet",
            api_key=api_key,
            base_url="https://openai.qiniu.com/v1",
            timeout=180)  # 添加超时设置
        
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
        
        self.image_generator = ImageGeneratorAgent(
            task_id=str(self.id),
            config=ImageGeneratorConfig(
                qiniu_api_key=api_key
            )
        )
        
        self.voice_synthesizer = VoiceSynthesizerAgent(
            task_id=str(self.id),
            config=VoiceSynthesizerConfig(
                qiniu_api_key=api_key
            )
        )
        
        self.video_composer = VideoComposerAgent(
            task_id=str(self.id),
            config=VideoComposerConfig()
        )

        self.progress_tracker = progress_tracker
    
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
        await self.progress_tracker.update(self.id, "开始执行", 1, "开始执行")

        # 1. 小说解析
        print("1. 开始解析小说...")
        await self.progress_tracker.update(self.id, "小说解析中", 15, "小说解析中")
        novel_data = await self.novel_parser.execute(novel_text)
        await self.progress_tracker.update(self.id, "小说解析完成", 20, "小说解析完成")
        print("小说解析完成")
        
        # 2. 分镜设计
        print("2. 开始分镜设计...")
        await self.progress_tracker.update(self.id, "分镜设计中", 30, "分镜设计中")
        storyboard_data = await self.storyboard.create(novel_data)
        await self.progress_tracker.update(self.id, "分镜设计完成", 40, "分镜设计完成")
        print("分镜设计完成")
        
        # 3. 角色一致性管理
        print("3. 管理角色一致性...")
        await self.progress_tracker.update(self.id, "角色一致性管理中", 50, "角色一致性管理中")
        character_data = await self.character_consistency.execute(
            novel_data.get("characters", []), 
            self.id
        )
        await self.progress_tracker.update(self.id, "角色一致性管理完成", 60, "角色一致性管理完成")
        print("角色管理完成")
        
        # 4. 并行生成图片和音频
        print("4. 开始生成图片和音频...")
        await self.progress_tracker.update(self.id, "图片和音频生成中", 70, "图片和音频生成中")
        
        # 从 chapters 中提取所有 scenes
        scenes = []
        for chapter in storyboard_data.get("chapters", []):
            scenes.extend(chapter.get("scenes", []))
        
        characters = novel_data.get("characters", [])
        
        # 创建角色信息字典，便于根据角色名查找
        character_dict = {char["name"]: char for char in characters}
        
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
            # 获取场景中的对话
            dialogue_list = scene.get("dialogue", [])
            if dialogue_list:
                # 使用新的对话合成功能
                audio_task = self.voice_synthesizer.synthesize_dialogue(
                    dialogues=dialogue_list,
                    characters_info=character_dict
                )
                audio_tasks.append(audio_task)
            else:
                # 如果没有对话，使用场景描述，则静音
                audio_task = self.voice_synthesizer.execute(
                    text="",
                    character=None,
                    character_info=None
                )
                audio_tasks.append(audio_task)
        
        # 串行执行所有图像和音频生成任务，每次执行完后等待1秒
        images = []
        raw_audios = []
        
        for i, (image_task, audio_task) in enumerate(zip(image_tasks, audio_tasks)):
            print(f"处理场景 {i+1}/{len(image_tasks)}...")
            
            # 执行图像生成任务
            image = await image_task
            images.append(image)
            
            # 执行音频生成任务
            audio = await audio_task
            raw_audios.append(audio)
            
            # 等待1秒再执行下一个任务
            if i < len(image_tasks) - 1:  # 最后一个任务不需要等待
                print(f"等待1秒...")
                await asyncio.sleep(1)
        
        # 处理音频数据，确保每个场景只有一个音频文件
        # 如果synthesize_dialogue返回了音频列表，需要将它们合并
        processed_audios = []
        for i, audio in enumerate(raw_audios):
            if isinstance(audio, list):
                # 如果是列表，说明是多个音频文件，需要合并
                if len(audio) == 1:
                    # 只有一个音频文件，直接使用
                    processed_audios.append(audio[0])
                elif len(audio) > 1:
                    # 多个音频文件，需要合并
                    merged_audio_path = await self._merge_audio_files(audio, f"scene_{i}_merged.mp3")
                    processed_audios.append(merged_audio_path)
                else:
                    # 没有音频文件，使用默认音频
                    default_audio = await self.voice_synthesizer.execute(
                        text="",
                        character=None,
                        character_info=None
                    )
                    processed_audios.append(default_audio)
            else:
                # 单个音频文件，直接使用
                processed_audios.append(audio)
        
        await self.progress_tracker.update(self.id, "图片和音频生成完成", 90, "图片和音频生成完成")
        print("图片和音频生成完成")
        # 5. 视频合成
        print("5. 开始合成视频...")
        await self.progress_tracker.update(self.id, "视频合成中", 95, "视频合成中")
        video_result = await self.video_composer.execute(images, processed_audios, storyboard_data)
        await self.progress_tracker.update(self.id, "视频合成完成", 100, "视频合成完成")
        print("视频合成完成")
        # 当前使用本地路径
        print(f"视频保存路径 url：{video_result.get('url', '')}")
        await self.progress_tracker.complete(self.id, video_result.get("url", ""))
        return {
            "video_path": video_result.get("url", ""),
            "scenes_count": len(scenes)
        }
    
    async def _merge_audio_files(self, audio_files: List[str], output_filename: str) -> str:
        """
        合并多个音频文件为一个音频文件
        
        Args:
            audio_files: 音频文件路径列表
            output_filename: 输出文件名
            
        Returns:
            str: 合并后的音频文件路径
        """
        try:
            import subprocess
            import asyncio
            from pathlib import Path
            
            # 创建临时文件列表
            temp_dir = Path("./data/temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            file_list_path = temp_dir / f"file_list_{uuid4()}.txt"
            with open(file_list_path, "w") as f:
                for audio_file in audio_files:
                    # 确保使用绝对路径
                    abs_path = os.path.abspath(audio_file)
                    f.write(f"file '{abs_path}'\n")
            
            # 输出文件路径
            output_path = temp_dir / output_filename
            
            # 使用FFmpeg合并音频
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(file_list_path),
                "-c", "copy",
                str(output_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            # 清理临时文件列表
            file_list_path.unlink()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise Exception(f"FFmpeg audio merge failed: {error_msg}")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to merge audio files: {e}")
            # 如果合并失败，返回第一个音频文件
            return audio_files[0] if audio_files else ""