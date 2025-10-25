from typing import Dict, List, Any, Optional, cast
import logging
import uuid
import io
import base64
import json

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
        self._validate_input(text)
        
        audio_data = await self._call_tts(text)
        
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
    
    async def _call_tts(self, text: str) -> bytes:
        try:
            config = cast(VoiceSynthesizerConfig, self.config)
            # 准备请求参数
            params = {
                "audio": {
                    "voice_type": config.voice_type,
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
        if not text or len(text.strip()) == 0:
            raise ValidationError("Text cannot be empty")
        
        if len(text) > config.max_text_length:
            raise ValidationError(
                f"Text too long. Maximum {config.max_text_length} characters allowed"
            )