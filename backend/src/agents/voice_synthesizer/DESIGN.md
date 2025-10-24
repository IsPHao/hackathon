# Voice Synthesizer Agent 设计文档

## 1. Agent概述

### 1.1 职责
语音合成Agent负责为场景对话生成语音，支持多角色声音区分。

### 1.2 核心功能
- 文本转语音
- 多角色声音管理
- 音频后处理
- 音频上传

## 2. 模型选择

| 服务 | 音质 | 克隆 | 成本 | 场景 |
|------|------|------|------|------|
| OpenAI TTS | ⭐⭐⭐⭐ | ❌ | $15/1M字符 | Phase 1 |
| ElevenLabs | ⭐⭐⭐⭐⭐ | ✅ | $0.30/1K字符 | Phase 2 |
| Fish Audio | ⭐⭐⭐⭐ | ✅ | 免费 | 备选 |

## 3. 核心实现

```python
class VoiceSynthesizerAgent:
    
    def __init__(self, tts_client, storage_service):
        self.tts_client = tts_client
        self.storage = storage_service
        self.voice_mapping = self._initialize_voices()
    
    def _initialize_voices(self) -> Dict[str, str]:
        """初始化角色声音映射"""
        return {
            "male_young": "alloy",
            "male_adult": "onyx",
            "female_young": "nova",
            "female_adult": "shimmer",
            "narrator": "fable"
        }
    
    async def synthesize(
        self,
        text: str,
        character: str,
        character_info: Optional[Dict] = None
    ) -> str:
        """合成语音"""
        # 1. 选择声音
        voice = self._select_voice(character, character_info)
        
        # 2. 调用TTS
        audio = await self._call_tts(text, voice)
        
        # 3. 后处理
        audio = await self._post_process(audio)
        
        # 4. 上传
        audio_url = await self._upload_audio(audio)
        
        return audio_url
    
    def _select_voice(
        self,
        character: str,
        character_info: Optional[Dict]
    ) -> str:
        """选择合适的声音"""
        if not character_info:
            return self.voice_mapping["narrator"]
        
        gender = character_info.get("appearance", {}).get("gender", "male")
        age = character_info.get("appearance", {}).get("age", 20)
        
        if gender == "male":
            return self.voice_mapping["male_young"] if age < 25 else self.voice_mapping["male_adult"]
        else:
            return self.voice_mapping["female_young"] if age < 25 else self.voice_mapping["female_adult"]
    
    async def _call_tts(self, text: str, voice: str) -> bytes:
        """调用TTS API"""
        response = await self.tts_client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            speed=1.0
        )
        
        return response.content
    
    async def generate_batch(
        self,
        dialogues: List[Dict]
    ) -> List[str]:
        """批量生成语音"""
        tasks = [
            self.synthesize(
                d["text"],
                d["character"],
                d.get("character_info")
            )
            for d in dialogues
        ]
        
        return await asyncio.gather(*tasks)
```

## 4. 音频处理

```python
from pydub import AudioSegment

async def _post_process(self, audio: bytes) -> bytes:
    """音频后处理"""
    # 加载音频
    audio_seg = AudioSegment.from_mp3(io.BytesIO(audio))
    
    # 音量归一化
    audio_seg = audio_seg.normalize()
    
    # 添加淡入淡出
    audio_seg = audio_seg.fade_in(100).fade_out(100)
    
    # 导出
    output = io.BytesIO()
    audio_seg.export(output, format="mp3", bitrate="128k")
    
    return output.getvalue()
```

## 5. 性能指标

- 生成速度: 2s/句 (OpenAI TTS)
- 成功率: >98%
- 音质评分: >90%
- 批量吞吐: 100句/5分钟
