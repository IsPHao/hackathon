# Agent 模块重构文档

## 重构概述

本次重构优化了 `backend/src/agents/` 下的所有模块,提取了可重用的工具和组件,统一了文件存储策略。

## 主要变更

### 1. 创建共享基础模块 (`src/agents/base/`)

#### 1.1 基础异常类 (`base/exceptions.py`)
- 提取了所有 Agent 共用的异常基类
- 包含: `BaseAgentError`, `ValidationError`, `APIError`, `StorageError`, `ProcessError`, `ParseError`, `GenerationError`, `SynthesisError`, `CompositionError`, `DownloadError`

#### 1.2 统一存储接口 (`base/storage.py`)
- 合并了 `image_generator/storage.py` 和 `video_composer/storage.py` 的重复代码
- 提供统一的 `StorageBackend` 抽象类
- 实现: `LocalStorage`, `OSSStorage`, `create_storage()` 工厂函数
- 支持两种保存方式: `save(data, filename)` 和 `save_file(filepath, filename)`

#### 1.3 任务存储管理器 (`base/task_storage.py`)
- 新增基于任务ID的文件组织结构
- 自动创建目录: `data/tasks/{task_id}/images/`, `audio/`, `temp/`
- 提供专门的保存方法: `save_image()`, `save_audio()`, `save_temp()`
- 支持临时文件清理: `cleanup_temp()`

#### 1.4 LLM 工具 (`base/llm_utils.py`)
- 提取了 3 个 Agent 中 95% 相同的 LLM JSON 调用代码
- `LLMJSONMixin` 提供统一的 `_call_llm_json()` 方法

#### 1.5 下载工具 (`base/download_utils.py`)
- 提供异步文件下载功能
- `download_to_bytes()`: 下载为字节
- `download_file()`: 下载并保存到文件

#### 1.6 Base Agent 类 (`base/agent.py`)
- 提供 Agent 基类,包含通用验证方法
- `_validate_not_empty()`, `_validate_type()`, `_validate_list_not_empty()`

### 2. Agent 模块重构

#### 2.1 ImageGeneratorAgent
**变更:**
- ❌ 移除 OSS 存储配置 (oss_bucket, oss_endpoint, oss_access_key, oss_secret_key)
- ✅ 改用 `TaskStorageManager` 进行本地任务存储
- ✅ 新增 `task_id` 必需参数
- ✅ 图片保存到 `data/tasks/{task_id}/images/`
- ✅ 使用 `base.download_to_bytes()` 替代内部下载方法

**API 变更:**
```python
before:
ImageGeneratorAgent(openai_client, config, storage)

after:
ImageGeneratorAgent(openai_client, task_id, config)
```

#### 2.2 VoiceSynthesizerAgent
**变更:**
- ❌ 移除 `tempfile` 临时文件使用
- ✅ 改用 `TaskStorageManager` 进行本地任务存储
- ✅ 新增 `task_id` 必需参数
- ✅ 音频保存到 `data/tasks/{task_id}/audio/`
- ✅ 新增配置项 `task_storage_base_path`

**API 变更:**
```python
before:
VoiceSynthesizerAgent(client, config)

after:
VoiceSynthesizerAgent(client, task_id, config)
```

#### 2.3 VideoComposerAgent
**变更:**
- ❌ 移除 `temp_dir` 配置项 (原默认值 "/tmp/video_composition")
- ✅ 改用 `TaskStorageManager.temp_dir`
- ✅ 新增 `task_id` 必需参数
- ✅ 临时文件保存到 `data/tasks/{task_id}/temp/`
- ✅ 最终视频仍支持 OSS/本地存储 (符合需求)
- ✅ 使用 `base.create_storage()` 替代模块内 storage
- ✅ 使用 `base.download_file()` 替代内部下载方法

**API 变更:**
```python
before:
VideoComposerAgent(config, storage)

after:
VideoComposerAgent(task_id, config, storage)
```

### 3. 文件存储策略变更

#### 3.1 新的文件组织结构
```
data/
├── tasks/                          # 任务相关文件 (临时)
│   └── {task_id}/
│       ├── images/                 # image_generator 输出
│       ├── audio/                  # voice_synthesizer 输出
│       └── temp/                   # video_composer 临时文件
├── characters/                     # character_consistency 持久化
│   └── {project_id}/
│       └── {character}.json
└── videos/                         # 最终视频输出 (持久化)
    └── {video_id}.mp4
```

#### 3.2 存储策略对比

| Agent | 之前 | 之后 |
|-------|------|------|
| image_generator | OSS/local 可配置 | **本地任务存储** (data/tasks/{task_id}/images/) |
| voice_synthesizer | 系统临时目录 | **本地任务存储** (data/tasks/{task_id}/audio/) |
| video_composer (临时) | /tmp/video_composition | **本地任务存储** (data/tasks/{task_id}/temp/) |
| video_composer (最终) | OSS/local 可配置 | ✅ **保持不变** (OSS/local) |
| character_consistency | 本地持久化 | ✅ **保持不变** (data/characters/) |

### 4. 删除的重复代码

#### 4.1 删除的文件
- `backend/src/agents/image_generator/storage.py` (96 行) → 合并到 `base/storage.py`
- `backend/src/agents/video_composer/storage.py` (141 行) → 合并到 `base/storage.py`

#### 4.2 代码精简统计
- **删除重复存储代码**: ~200 行
- **LLM JSON 调用统一**: 减少 ~60 行重复代码 (3个Agent)
- **异常类统一**: 减少 ~100 行重复定义
- **总计**: 约减少 **360+ 行重复代码** (不含注释)

## 迁移指南

### 对于使用 ImageGeneratorAgent 的代码

```python
from openai import AsyncOpenAI
from agents.image_generator import ImageGeneratorAgent

client = AsyncOpenAI(api_key="...")

agent = ImageGeneratorAgent(
    openai_client=client,
    task_id="task_12345",  # 新增必需参数
)

image_path = await agent.generate(scene_data, character_templates)
```

### 对于使用 VoiceSynthesizerAgent 的代码

```python
from openai import AsyncOpenAI
from agents.voice_synthesizer import VoiceSynthesizerAgent

client = AsyncOpenAI(api_key="...")

agent = VoiceSynthesizerAgent(
    client=client,
    task_id="task_12345",  # 新增必需参数
)

audio_path = await agent.synthesize(text, character_info=char_info)
```

### 对于使用 VideoComposerAgent 的代码

```python
from agents.video_composer import VideoComposerAgent

agent = VideoComposerAgent(
    task_id="task_12345",  # 新增必需参数
    config=config,
    storage=storage  # 可选,用于最终视频存储
)

video_info = await agent.compose(images, audios, storyboard)
```

## 配置变更

### ImageGeneratorConfig
```python
removed:
- storage_type: Literal["local", "oss"]
- local_storage_path: str
- oss_bucket, oss_endpoint, oss_access_key, oss_secret_key

added:
+ task_storage_base_path: str = "./data/tasks"
```

### VoiceSynthesizerConfig
```python
added:
+ task_storage_base_path: str = "./data/tasks"
```

### VideoComposerConfig
```python
removed:
- temp_dir: str = "/tmp/video_composition"

added:
+ task_storage_base_path: str = "./data/tasks"

kept:
✓ storage_type: Literal["local", "oss"]  # 用于最终视频
✓ local_storage_path: str
✓ oss_* configurations
```

## 测试更新

所有受影响的 Agent 测试需要更新:
- 测试初始化时传入 `task_id` 参数
- 验证文件保存到正确的任务目录
- 移除 OSS 相关测试 (image_generator)
- 更新文件路径断言

## 优势总结

### 1. 代码重用
- ✅ 3 个存储实现合并为 1 个
- ✅ LLM JSON 调用逻辑统一
- ✅ 异常类层次结构统一

### 2. 文件组织
- ✅ 按任务ID组织文件,便于管理和清理
- ✅ 临时文件与持久化文件分离
- ✅ 清晰的目录结构

### 3. 存储策略
- ✅ 符合需求: 只有 video_composer 最终输出支持 OSS
- ✅ 其他 Agent 的临时文件统一存储到本地任务文件夹
- ✅ 支持按任务清理临时文件

### 4. 可维护性
- ✅ 减少了 360+ 行重复代码
- ✅ 统一的接口和模式
- ✅ 更易于扩展和修改

## Breaking Changes

⚠️ **不兼容变更**:
1. `ImageGeneratorAgent`, `VoiceSynthesizerAgent`, `VideoComposerAgent` 的构造函数签名变更
2. `ImageGeneratorAgent` 不再支持 OSS 存储
3. `VideoComposerAgent` 不再支持自定义 temp_dir
4. 所有 Agent 都需要传入 `task_id` 参数

## 后续工作建议

1. ✅ 完成 Base Agent 类的继承 (novel_parser, storyboard, character_consistency)
2. ✅ 使用 LLMJSONMixin 统一 LLM 调用
3. ✅ 创建 base 模块的单元测试
4. ⏳ 更新所有 Agent 的集成测试
5. ⏳ 更新 API 层代码以传入 task_id
6. ⏳ 添加任务文件自动清理机制
