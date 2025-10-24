from typing import Dict, List, Any, Optional
import logging
import uuid
import io

from openai import AsyncOpenAI

from .config import VoiceSynthesizerConfig
from ..base import TaskStorageManager
from ..base.agent import BaseAgent
from .exceptions import ValidationError, SynthesisError, APIError

logger = logging.getLogger(__name__)


class VoiceSynthesizerAgent(BaseAgent[VoiceSynthesizerConfig]):
    
    def __init__(
        self,
        client: AsyncOpenAI,
        task_id: str,
        config: Optional[VoiceSynthesizerConfig] = None,
    ):
        super().__init__(config)
        self.client = client
        self.voice_mapping = self.config.voice_mapping
        self.task_storage = TaskStorageManager(
            task_id,
            base_path=self.config.task_storage_base_path
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
        return await self.synthesize(text, character, character_info, kwargs.get("voice"))
    
    async def health_check(self) -> bool:
        """健康检查:测试OpenAI TTS API连接"""
        try:
            models = await self.client.models.list()
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
        voice: Optional[str] = None,
    ) -> str:
        self._validate_input(text)
        
        selected_voice = voice or self._select_voice(character, character_info)
        
        audio_data = await self._call_tts(text, selected_voice)
        
        if self.config.enable_post_processing:
            try:
                from pydub import AudioSegment
                audio_data = await self._post_process(audio_data)
            except ImportError:
                logger.warning("pydub not available, skipping post-processing")
        
        filename = f"{uuid.uuid4()}.{self.config.audio_format}"
        audio_path = await self.task_storage.save_audio(audio_data, filename)
        
        return audio_path
    
    def _select_voice(
        self,
        character: Optional[str],
        character_info: Optional[Dict]
    ) -> str:
        if not character_info:
            return self.voice_mapping["narrator"]
        
        appearance = character_info.get("appearance", {})
        gender = appearance.get("gender", "male")
        age = appearance.get("age", 20)
        
        if gender == "male":
            return self.voice_mapping["male_young"] if age < 25 else self.voice_mapping["male_adult"]
        else:
            return self.voice_mapping["female_young"] if age < 25 else self.voice_mapping["female_adult"]
    
    async def _call_tts(self, text: str, voice: str) -> bytes:
        try:
            response = await self.client.audio.speech.create(
                model=self.config.model,
                voice=voice,
                input=text,
                speed=self.config.speed
            )
            
            return response.content
        
        except Exception as e:
            logger.error(f"TTS API call failed: {e}")
            raise APIError(f"Failed to call TTS API: {e}") from e
    
    async def _post_process(self, audio_data: bytes) -> bytes:
        try:
            from pydub import AudioSegment
            
            audio_seg = AudioSegment.from_mp3(io.BytesIO(audio_data))
            
            audio_seg = audio_seg.normalize()
            
            if self.config.fade_duration > 0:
                audio_seg = audio_seg.fade_in(self.config.fade_duration).fade_out(self.config.fade_duration)
            
            output = io.BytesIO()
            audio_seg.export(output, format=self.config.audio_format, bitrate="128k")
            
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
                d.get("character_info"),
                d.get("voice")
            )
            for d in dialogues
        ]
        
        return await asyncio.gather(*tasks)
    
    def _validate_input(self, text: str):
        if not text or len(text.strip()) == 0:
            raise ValidationError("Text cannot be empty")
        
        if len(text) > self.config.max_text_length:
            raise ValidationError(
                f"Text too long. Maximum {self.config.max_text_length} characters allowed"
            )
