# Services 模块设计文档

## 1. 模块概述

Services模块负责封装所有外部服务的调用，提供统一的接口和错误处理。

## 2. 服务列表

### 2.1 LLM Service
```python
class LLMService:
    """大语言模型服务"""
    
    async def chat_completion(
        self,
        messages: List[Dict],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7
    ) -> str:
        """聊天补全"""
        pass
    
    async def json_completion(
        self,
        prompt: str,
        model: str = "gpt-4o-mini"
    ) -> Dict:
        """JSON格式输出"""
        pass
```

### 2.2 Image Service
```python
class ImageService:
    """图像生成服务"""
    
    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard"
    ) -> bytes:
        """生成图片"""
        pass
```

### 2.3 TTS Service
```python
class TTSService:
    """文本转语音服务"""
    
    async def synthesize(
        self,
        text: str,
        voice: str = "alloy"
    ) -> bytes:
        """合成语音"""
        pass
```

### 2.4 Storage Service
```python
class StorageService:
    """对象存储服务（七牛云）"""
    
    async def upload(
        self,
        file_data: bytes,
        file_name: str,
        content_type: str
    ) -> str:
        """上传文件"""
        pass
    
    async def download(self, url: str) -> bytes:
        """下载文件"""
        pass
    
    async def get_cdn_url(self, key: str) -> str:
        """获取CDN URL"""
        pass
```

### 2.5 Cache Service
```python
class CacheService:
    """缓存服务（Redis）"""
    
    async def get(self, key: str) -> Optional[str]:
        """获取缓存"""
        pass
    
    async def set(
        self,
        key: str,
        value: str,
        ttl: int = 3600
    ):
        """设置缓存"""
        pass
    
    async def delete(self, key: str):
        """删除缓存"""
        pass
```

## 3. 错误处理

```python
class ServiceError(Exception):
    """服务错误基类"""
    pass

class APIRateLimitError(ServiceError):
    """API限流错误"""
    pass

class APITimeoutError(ServiceError):
    """API超时错误"""
    pass
```

## 4. 重试机制

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_with_retry(func, *args, **kwargs):
    """带重试的调用"""
    return await func(*args, **kwargs)
```

## 5. 监控

- API调用次数
- API响应时间
- 错误率
- 成本统计
