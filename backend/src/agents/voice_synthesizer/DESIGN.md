# Voice Synthesizer Agent 设计文档

## 1. Agent概述

### 1.1 职责
语音合成Agent负责为场景对话生成语音，支持多角色声音区分。

### 1.2 核心功能
- 文本转语音
- 音频后处理
- 音频上传

## 2. 模型选择

| 服务 | 音质 | 克隆 | 成本 | 场景 |
|------|------|------|------|------|
| Qiniu TTS | ⭐⭐⭐⭐ | ❌ | 按量计费 | 默认 |
| OpenAI TTS | ⭐⭐⭐⭐ | ❌ | $15/1M字符 | 原始方案 |
| ElevenLabs | ⭐⭐⭐⭐⭐ | ✅ | $0.30/1K字符 | Phase 2 |
| Fish Audio | ⭐⭐⭐⭐ | ✅ | 免费 | 备选 |

## 3. 核心实现

```python
class VoiceSynthesizerAgent:
    
    def __init__(self, config: VoiceSynthesizerConfig, storage_service):
        self.config = config
        self.storage = storage_service
    
    async def synthesize(
        self,
        text: str,
        character: str,
        character_info: Optional[Dict] = None
    ) -> str:
        """合成语音"""
        # 1. 调用TTS
        audio = await self._call_tts(text)
        
        # 2. 后处理
        audio = await self._post_process(audio)
        
        # 3. 上传
        audio_url = await self._upload_audio(audio)
        
        return audio_url
    
    async def _call_tts(self, text: str) -> bytes:
        """调用七牛云TTS API"""
        # 准备请求参数
        params = {
            "audio": {
                "voice_type": self.config.voice_type,
                "encoding": self.config.encoding,
                "speed_ratio": self.config.speed_ratio
            },
            "request": {
                "text": text
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.config.qiniu_api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.config.qiniu_endpoint}/voice/tts"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise APIError(f"Qiniu TTS API error: {response.status} - {error_text}")
                
                result = await response.json()
                
                # 解析七牛云API响应
                if "data" not in result:
                    raise SynthesisError("Invalid response from Qiniu TTS API: no audio data")
                
                # 获取base64编码的音频数据
                audio_b64 = result["data"]
                if not audio_b64:
                    raise SynthesisError("Invalid response from Qiniu TTS API: no base64 audio data")
                
                # 解码base64音频数据
                audio_data = base64.b64decode(audio_b64)
                return audio_data
    
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

## 5. API集成

### 5.1 七牛云TTS API

使用七牛云AI API进行文本到语音的生成。

请求示例：
```bash
export OPENAI_BASE_URL="https://openai.qiniu.com/v1"
export OPENAI_API_KEY="<你的七牛云 AI API KEY>"

curl --location "$OPENAI_BASE_URL/voice/tts" \
--header "Content-Type: application/json" \
--header "Authorization: Bearer $OPENAI_API_KEY" \
--data '{
  "audio": {
    "voice_type": "qiniu_zh_female_wwxkjx",
    "encoding": "mp3",
    "speed_ratio": 1.0
  },
  "request": {
    "text": "你好，世界！"
  }
}'
```

### 5.2 响应格式处理

七牛云AI API返回以下格式的响应：

```json
{
  "reqid": "f3dff20d7d670df7adcb2ff0ab5ac7ea",
  "operation": "query",
  "sequence": -1,
  "data": "data",
  "addition": { "duration": "1673" }
}
```

我们的实现会解析[data](file:///home/ubuntu/workspace/demo/hackathon/backend/src/agents/base/storage.py#L28-L28)字段作为base64编码的音频数据，并将其解码为音频数据。

## 6. 性能指标

- 生成速度: 1s/句 (七牛云TTS)
- 成功率: >98%
- 音质评分: >90%
- 批量吞吐: 100句/5分钟