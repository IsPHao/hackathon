from typing import Dict, List, Any, Optional, cast
import logging
import uuid
import io
import base64
import json
import asyncio

import aiohttp
from aiohttp import ClientTimeout

from .config import VoiceSynthesizerConfig
from ..base import TaskStorageManager
from ..base.agent import BaseAgent
from ..base.exceptions import ValidationError, SynthesisError, APIError

logger = logging.getLogger(__name__)


class VoiceSynthesizerAgent(BaseAgent[VoiceSynthesizerConfig]):
    
    def __init__(
        self,
        task_id: str,
        config: Optional[VoiceSynthesizerConfig] = None,
    ):
        super().__init__(config)
        self.task_storage = TaskStorageManager(
            task_id,
            base_path=config.task_storage_base_path if config else "./data/tasks"
        )
    
    def _default_config(self) -> VoiceSynthesizerConfig:
        return VoiceSynthesizerConfig()
    
    async def execute(self, text: str, character: Optional[str] = None, character_info: Optional[Dict] = None, **kwargs) -> str:
        """
        执行语音合成(统一接口)
        
        Args:
            text: 要合成的文本
            character: 角色名称
            character_info: 角色信息
            **kwargs: 其他参数
        
        Returns:
            str: 音频路径
        """
        return await self.synthesize(text, character, character_info)
    
    async def synthesize_dialogue(
        self,
        dialogues: List[Dict[str, Any]],
        characters_info: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        批量合成对话音频
        
        Args:
            dialogues: 对话列表，格式为 [{"character": "角色名", "text": "对话内容"}, ...]
            characters_info: 角色信息字典，用于确定语音类型
            
        Returns:
            List[str]: 音频路径列表
        """
        tasks = []
        for dialogue in dialogues:
            character_name = dialogue.get("character")
            text = dialogue.get("text", "")
            character_info = characters_info.get(character_name) if characters_info and character_name else None
            
            task = self.synthesize(text, character_name, character_info)
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    async def health_check(self) -> bool:
        """健康检查:测试七牛云TTS API连接"""
        try:
            # 简单测试，发送一个短文本
            test_text = "你好"
            await self._call_tts(test_text)
            self.logger.info("VoiceSynthesizerAgent health check: OK")
            return True
        except Exception as e:
            self.logger.error(f"VoiceSynthesizerAgent health check failed: {e}")
            return False
    
    async def synthesize(
        self,
        text: str,
        character: Optional[str] = None,
        character_info: Optional[Dict] = None,
    ) -> str:
        # 如果文本为空，生成一段空的音频
        if not text or len(text.strip()) == 0:
            return await self._generate_silent_audio()
        
        self._validate_input(text)
        
        # 根据角色性别选择语音类型
        voice_type = self._select_voice_type(character_info)
        
        audio_data = await self._call_tts(text, voice_type)
        
        config = cast(VoiceSynthesizerConfig, self.config)
        if config.enable_post_processing:
            try:
                from pydub import AudioSegment
                audio_data = await self._post_process(audio_data)
            except ImportError:
                logger.warning("pydub not available, skipping post-processing")
        
        filename = f"{uuid.uuid4()}.{config.audio_format}"
        audio_path = await self.task_storage.save_audio(audio_data, filename)
        
        return audio_path
    
    def _select_voice_type(self, character_info: Optional[Dict] = None) -> str:
        """
        根据角色信息选择语音类型
        
        Args:
            character_info: 角色信息
            
        Returns:
            str: 语音类型
        """
        config = cast(VoiceSynthesizerConfig, self.config)
        default_voice_type = config.voice_type
        
        if not character_info:
            return default_voice_type
            
        appearance = character_info.get("appearance", {})
        gender = appearance.get("gender", "").lower()
        
        if gender == "male":
            return "qiniu_zh_male_ljfdxz"
        elif gender == "female":
            return "qiniu_zh_female_wwxkjx"
        else:
            return default_voice_type
    
    async def _call_tts(self, text: str, voice_type: Optional[str] = None) -> bytes:
        try:
            config = cast(VoiceSynthesizerConfig, self.config)
            # 使用传入的voice_type或配置中的默认voice_type
            selected_voice_type = voice_type if voice_type else config.voice_type
            
            # 准备请求参数
            params = {
                "audio": {
                    "voice_type": selected_voice_type,
                    "encoding": config.encoding,
                    "speed_ratio": config.speed_ratio
                },
                "request": {
                    "text": text
                }
            }
            
            headers = {
                "Authorization": f"Bearer {config.qiniu_api_key}",
                "Content-Type": "application/json"
            }
            
            url = f"{config.qiniu_endpoint}/v1/voice/tts"
            
            timeout = ClientTimeout(total=30)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params, headers=headers, timeout=timeout) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise APIError(f"Qiniu TTS API error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    
                    # 根据七牛云API文档解析响应
                    if "data" not in result:
                        raise SynthesisError("Invalid response from Qiniu TTS API: no audio data")
                    
                    # 获取base64编码的音频数据
                    audio_b64 = result["data"]
                    if not audio_b64:
                        raise SynthesisError("Invalid response from Qiniu TTS API: no base64 audio data")
                    
                    # 解码base64音频数据
                    audio_data = base64.b64decode(audio_b64)
                    return audio_data
        
        except Exception as e:
            logger.error(f"TTS API call failed: {e}")
            raise APIError(f"Failed to call TTS API: {e}") from e
    
    async def _post_process(self, audio_data: bytes) -> bytes:
        try:
            from pydub import AudioSegment
            
            config = cast(VoiceSynthesizerConfig, self.config)
            audio_seg = AudioSegment.from_mp3(io.BytesIO(audio_data))
            
            audio_seg = audio_seg.normalize()
            
            if config.fade_duration > 0:
                audio_seg = audio_seg.fade_in(config.fade_duration).fade_out(config.fade_duration)
            
            output = io.BytesIO()
            audio_seg.export(output, format=config.audio_format, bitrate="128k")
            
            return output.getvalue()
        
        except Exception as e:
            logger.warning(f"Audio post-processing failed: {e}, returning original audio")
            return audio_data
    
    async def _generate_silent_audio(self, duration: float = 3.0) -> str:
        """
        使用FFmpeg生成一段空音频
        
        Args:
            duration: 音频时长（秒）
            
        Returns:
            str: 空音频文件路径
        """
        try:
            import subprocess
            import asyncio
            
            # 创建临时文件路径
            filename = f"{uuid.uuid4()}.mp3"
            temp_path = self.task_storage.temp_dir / filename
            
            # 使用FFmpeg生成静音音频
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "lavfi",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t", str(duration),
                "-q:a", "9",
                str(temp_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.warning(f"FFmpeg silent audio generation failed: {error_msg}")
                # 如果FFmpeg失败，回退到创建一个空的MP3文件
                temp_path.write_bytes(b"")
            
            # 将文件移动到正确的位置
            final_path = await self.task_storage.save_audio(temp_path.read_bytes(), filename)
            
            # 删除临时文件
            if temp_path.exists():
                temp_path.unlink()
            
            return final_path
            
        except Exception as e:
            logger.warning(f"Failed to generate silent audio: {e}")
            # 如果所有方法都失败，创建一个空的音频文件
            config = cast(VoiceSynthesizerConfig, self.config)
            filename = f"{uuid.uuid4()}.{config.audio_format}"
            return await self.task_storage.save_audio(b"", filename)
    
    async def generate_batch(
        self,
        dialogues: List[Dict]
    ) -> List[str]:
        import asyncio
        
        tasks = [
            self.synthesize(
                d["text"],
                d.get("character"),
                d.get("character_info")
            )
            for d in dialogues
        ]
        
        return await asyncio.gather(*tasks)
    
    def _validate_input(self, text: str):
        config = cast(VoiceSynthesizerConfig, self.config)
        # 移除对空文本的验证，因为我们现在支持生成空音频
        if len(text) > config.max_text_length:
            raise ValidationError(
                f"Text too long. Maximum {config.max_text_length} characters allowed"
            )