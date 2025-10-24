from typing import Dict, List, Any, Optional
import logging
import tempfile
import os
import io

from openai import AsyncOpenAI

from .config import VoiceSynthesizerConfig
from .exceptions import ValidationError, SynthesisError, APIError

logger = logging.getLogger(__name__)


class VoiceSynthesizerAgent:
    
    def __init__(
        self,
        client: AsyncOpenAI,
        config: Optional[VoiceSynthesizerConfig] = None,
    ):
        self.config = config or VoiceSynthesizerConfig()
        self.client = client
        self.voice_mapping = self.config.voice_mapping
    
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
        
        audio_path = await self._save_to_temp(audio_data)
        
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
    
    async def _save_to_temp(self, audio_data: bytes) -> str:
        try:
            with tempfile.NamedTemporaryFile(
                mode='wb',
                suffix=f'.{self.config.audio_format}',
                delete=False
            ) as temp_file:
                temp_file.write(audio_data)
                return temp_file.name
        
        except Exception as e:
            logger.error(f"Failed to save audio to temp file: {e}")
            raise SynthesisError(f"Failed to save audio: {e}") from e
    
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
