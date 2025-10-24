# Core Module

核心业务编排模块，负责协调各个 Agent 的执行，管理任务状态，跟踪进度，处理错误。

## 模块结构

```
core/
├── __init__.py           # 模块导出
├── pipeline.py           # 主工作流编排器
├── task_manager.py       # 任务管理器
├── progress_tracker.py   # 进度跟踪器
├── error_handler.py      # 错误处理器
├── interfaces.py         # 接口定义
├── exceptions.py         # 异常定义
├── config.py            # 配置管理
├── llm_factory.py       # LLM 工厂（支持不同模型）
├── DESIGN.md            # 设计文档
└── README.md            # 本文档
```

## 核心组件

### 1. AnimePipeline

主工作流编排器，协调整个视频生成流程。

**功能：**
- 编排 6 个 Agent 的执行顺序
- 管理数据在 Agent 之间的流转
- 实现自动重试机制
- 上报实时进度
- 处理并发任务

**使用示例：**

```python
from backend.src.core import AnimePipeline, ProgressTracker, ErrorHandler
from backend.src.agents.novel_parser import NovelParserAgent
from backend.src.agents.storyboard import StoryboardAgent
# ... 导入其他 agents

pipeline = AnimePipeline(
    novel_parser=NovelParserAgent(llm=llm),
    storyboard=StoryboardAgent(llm=llm),
    character_consistency=CharacterConsistencyAgent(llm=llm),
    image_generator=ImageGeneratorAgent(client=openai_client, task_id=task_id),
    voice_synthesizer=VoiceSynthesizerAgent(client=openai_client, task_id=task_id),
    video_composer=VideoComposerAgent(task_id=task_id),
    progress_tracker=ProgressTracker(redis_client),
    error_handler=ErrorHandler()
)

result = await pipeline.execute(
    project_id=project_id,
    novel_text=novel_text,
    options={"style": "anime"}
)
```

### 2. TaskManager

异步任务管理器，管理长时间运行的任务。

**功能：**
- 创建和管理异步任务
- 跟踪任务状态
- 支持任务取消
- 自动清理完成的任务

**使用示例：**

```python
from backend.src.core import TaskManager
from uuid import uuid4

task_manager = TaskManager()

async def my_task():
    # 执行耗时操作
    return "result"

task_id = uuid4()
task = await task_manager.create_task(
    task_id=task_id,
    project_id=project_id,
    task_type="video_generation",
    func=my_task
)

result = await task_manager.wait_for_task(task_id, timeout=3600)
```

### 3. ProgressTracker

进度跟踪器，实时上报任务进度。

**功能：**
- 初始化任务进度
- 更新进度信息
- 标记任务完成/失败
- 通过 Redis 发布进度更新（支持 WebSocket 推送）

**使用示例：**

```python
from backend.src.core import ProgressTracker

tracker = ProgressTracker(redis_client)

await tracker.initialize(project_id)
await tracker.update(project_id, "novel_parsing", 15, "小说解析完成")
await tracker.complete(project_id, video_url="http://example.com/video.mp4")
```

### 4. ErrorHandler

统一的错误处理器。

**功能：**
- 捕获和记录错误
- 错误分类（API 错误、验证错误、超时等）
- 错误上报（可集成 Sentry）
- 可恢复错误的自动重试

**使用示例：**

```python
from backend.src.core import ErrorHandler

handler = ErrorHandler()

try:
    await some_operation()
except Exception as e:
    await handler.handle(project_id, e, context={"operation": "image_generation"})
```

### 5. LLMFactory

LLM 工厂类，支持为不同 Agent 选择合适的 LLM。

**功能：**
- 根据 Agent 类型自动选择最合适的 LLM
- 支持不同能力的模型（JSON 模式、图像生成、语音合成等）
- 统一的 LLM 创建接口

**使用示例：**

```python
from backend.src.core import LLMFactory, LLMCapability

llm = LLMFactory.create_chat_llm("novel_parser", temperature=0.3)

recommended_model = LLMFactory.get_recommended_model(
    capability=LLMCapability.JSON_MODE,
    prefer_fast=True
)

openai_client = LLMFactory.create_openai_client()
```

**Agent LLM 映射：**

| Agent | 推荐模型 | 原因 |
|-------|---------|------|
| novel_parser | gpt-4o-mini | 需要 JSON 模式，追求性价比 |
| storyboard | gpt-4o-mini | 需要 JSON 模式，追求性价比 |
| character_consistency | gpt-4o | 需要更好的理解能力保证角色一致性 |
| image_generator | DALL-E 3 | OpenAI 图像生成 |
| voice_synthesizer | TTS-1 | OpenAI 语音合成 |

## 工作流程

```
用户输入小说文本
       ↓
1. 小说解析 (0-15%)
   - NovelParserAgent 解析角色、场景、对白
       ↓
2. 分镜设计 (15-30%)
   - StoryboardAgent 生成分镜脚本
       ↓
3. 角色一致性管理 (30-40%)
   - CharacterConsistencyAgent 生成角色参考图
       ↓
4. 并行生成内容 (40-80%)
   ├─→ ImageGeneratorAgent 生成场景图片 (40-70%)
   └─→ VoiceSynthesizerAgent 生成配音 (70-80%)
       ↓
5. 视频合成 (80-100%)
   - VideoComposerAgent 合成最终视频
       ↓
完成，返回视频 URL
```

## 配置

通过环境变量配置：

```bash
# Core 模块配置
CORE_MAX_RETRIES=3              # 最大重试次数
CORE_RETRY_BACKOFF_BASE=2       # 重试退避基数
CORE_TASK_TIMEOUT=3600          # 任务超时时间（秒）
CORE_CLEANUP_INTERVAL=3600      # 清理间隔（秒）

# OpenAI API
OPENAI_API_KEY=your_api_key_here
```

或通过代码配置：

```python
from backend.src.core import CoreSettings

config = CoreSettings(
    max_retries=5,
    retry_backoff_base=2,
    task_timeout=7200
)

pipeline = AnimePipeline(
    ...,
    config=config
)
```

## 错误处理

### 自动重试

Pipeline 会自动重试失败的操作，支持指数退避：

```python
# 第1次失败：等待 2^0 = 1 秒
# 第2次失败：等待 2^1 = 2 秒
# 第3次失败：等待 2^2 = 4 秒
# 之后抛出异常
```

### 错误分类

- **APIError**: API 调用失败（可恢复）
- **ValidationError**: 数据验证失败（不可恢复）
- **TimeoutError**: 操作超时（可恢复）
- **PipelineError**: Pipeline 执行失败（包装其他错误）

## 进度推送

进度通过 Redis Pub/Sub 实时推送，可通过 WebSocket 发送给前端：

**进度消息格式：**

```json
{
  "type": "progress",
  "project_id": "uuid",
  "status": "processing",
  "stage": "novel_parsing",
  "progress": 15,
  "message": "小说解析完成"
}
```

**完成消息格式：**

```json
{
  "type": "completed",
  "project_id": "uuid",
  "status": "completed",
  "progress": 100,
  "message": "视频生成完成",
  "video_url": "http://example.com/video.mp4"
}
```

**错误消息格式：**

```json
{
  "type": "error",
  "project_id": "uuid",
  "status": "failed",
  "error": "错误描述"
}
```

## 性能优化

### 并发处理

Pipeline 使用 `asyncio.gather` 并发执行独立任务：

```python
images, audios = await asyncio.gather(
    self._generate_images_with_progress(...),
    self._generate_audios_with_progress(...)
)
```

### 批量处理

ImageGeneratorAgent 和 VoiceSynthesizerAgent 支持批量处理：

```python
images = await image_generator.generate_batch(
    scenes=scenes,
    character_templates=character_data
)
```

## 测试

运行测试：

```bash
cd backend
pytest tests/core/ -v
```

测试覆盖：
- Pipeline 执行成功场景
- Pipeline 执行失败场景
- 自动重试机制
- 任务管理
- 进度跟踪
- 错误处理

## 集成示例

完整的集成示例：

```python
from uuid import uuid4
from backend.src.core import (
    AnimePipeline,
    ProgressTracker,
    ErrorHandler,
    LLMFactory,
)
from backend.src.agents.novel_parser import NovelParserAgent
from backend.src.agents.storyboard import StoryboardAgent
from backend.src.agents.character_consistency import CharacterConsistencyAgent
from backend.src.agents.image_generator import ImageGeneratorAgent
from backend.src.agents.voice_synthesizer import VoiceSynthesizerAgent
from backend.src.agents.video_composer import VideoComposerAgent

async def generate_anime_video(novel_text: str, redis_client):
    project_id = uuid4()
    task_id = str(project_id)
    
    novel_parser_llm = LLMFactory.create_chat_llm("novel_parser")
    storyboard_llm = LLMFactory.create_chat_llm("storyboard")
    character_llm = LLMFactory.create_chat_llm("character_consistency")
    openai_client = LLMFactory.create_openai_client()
    
    pipeline = AnimePipeline(
        novel_parser=NovelParserAgent(llm=novel_parser_llm),
        storyboard=StoryboardAgent(llm=storyboard_llm),
        character_consistency=CharacterConsistencyAgent(llm=character_llm),
        image_generator=ImageGeneratorAgent(
            openai_client=openai_client,
            task_id=task_id
        ),
        voice_synthesizer=VoiceSynthesizerAgent(
            client=openai_client,
            task_id=task_id
        ),
        video_composer=VideoComposerAgent(task_id=task_id),
        progress_tracker=ProgressTracker(redis_client),
        error_handler=ErrorHandler()
    )
    
    result = await pipeline.execute(project_id, novel_text)
    return result
```

## 扩展

### 添加新的 Agent

1. 在 `backend/src/agents/` 下创建新的 Agent 目录
2. 实现 Agent 类，继承或遵循现有 Agent 模式
3. 在 Pipeline 中添加新 Agent 的调用

### 支持新的 LLM

1. 在 `llm_factory.py` 中添加新的 LLMType
2. 定义该 LLM 支持的能力
3. 更新 AGENT_LLM_MAPPING 映射

### 自定义进度推送

继承 ProgressTracker，重写推送方法：

```python
class CustomProgressTracker(ProgressTracker):
    async def _publish_progress(self, project_id, progress_data):
        # 自定义推送逻辑
        await super()._publish_progress(project_id, progress_data)
        # 额外的推送（如 WebSocket、Webhook 等）
```

## 参考文档

- [整体设计文档](../../../DESIGN.md)
- [Core 模块设计](./DESIGN.md)
- [Agent 设计文档](../agents/*/DESIGN.md)
