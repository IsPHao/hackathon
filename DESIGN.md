# 智能动漫生成系统 - 整体架构设计

## 1. 项目概述

### 1.1 项目目标
构建一个智能动漫生成系统，能够自动将小说文本转换为动漫视频，支持角色一致性、多模态输出（图配文+声音）。

### 1.2 核心功能
- 自动根据小说文本生成动漫内容
- 保持角色在整个动漫中的视觉一致性
- 支持图配文+声音的伪视频形式
- 未来支持直接生成视频

### 1.3 技术约束
- 开发周期：3天（第一期MVP）
- 只能调用现有大模型API，无法预训练
- 优先实现基础功能，后续迭代优化

## 2. 系统架构

### 2.1 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                    前端层 (React/Vue + TS)                      │
│  - 小说输入界面                                                │
│  - 实时进度展示 (WebSocket)                                    │
│  - 视频预览播放                                                │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   API 网关层 (FastAPI)                         │
│  - RESTful API                                               │
│  - WebSocket (进度推送)                                       │
│  - 认证授权 / 限流                                            │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              任务编排层 (FastAPI BackgroundTasks)             │
│  - 异步任务处理                                               │
│  - 进度跟踪                                                  │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   核心业务层 (Agents)                          │
│                                                             │
│  ┌──────────────────┐     ┌──────────────────┐            │
│  │ NovelParserAgent │  →  │ StoryboardAgent  │            │
│  │  小说文本解析     │     │   分镜脚本设计    │            │
│  └──────────────────┘     └──────────────────┘            │
│           ↓                        ↓                       │
│    NovelParseResult         StoryboardResult               │
│                                    ↓                       │
│              ┌──────────────────────────┐                  │
│              │   SceneRenderer          │                  │
│              │   场景渲染（图片+音频）    │                  │
│              └──────────────────────────┘                  │
│                         ↓                                  │
│                   RenderResult                             │
│              (image_path + audio_path)                     │
│                         ↓                                  │
│              ┌──────────────────────────┐                  │
│              │   SceneComposer          │                  │
│              │   视频合成（FFmpeg）      │                  │
│              └──────────────────────────┘                  │
│                         ↓                                  │
│                  最终视频 (MP4)                             │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  数据持久化层                                  │
│  - PostgreSQL (关系数据库)                                    │
│  - Redis (缓存)                                              │
│  - Chroma (向量数据库)                                        │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   外部服务集成层                               │
│  - 七牛云 (存储+CDN)                                          │
│  - OpenAI API (LLM + TTS + DALL-E)                         │
│  - 其他大模型API                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈

#### 后端
- **框架**: FastAPI (Python 3.10+)
- **ORM**: SQLAlchemy
- **异步**: asyncio, aiohttp
- **任务队列**: FastAPI BackgroundTasks (Phase 1), Celery (Phase 2)
- **数据库**: PostgreSQL, Redis, Chroma

#### 前端
- **框架**: React 18+ / Vue 3+
- **语言**: TypeScript
- **状态管理**: Redux / Pinia
- **UI库**: Ant Design / Element Plus
- **通信**: Axios, WebSocket

#### AI/ML
- **LLM**: Claude 3.5 Sonnet (via 七牛云API)
- **图像生成**: 七牛云 Image Generation API
- **语音合成**: 七牛云 TTS API
- **视频处理**: FFmpeg

#### 基础设施
- **对象存储**: 七牛云
- **容器化**: Docker, Docker Compose
- **CI/CD**: GitHub Actions

## 3. 模块设计

### 3.1 API 模块 (`backend/src/api`)
负责HTTP接口和WebSocket通信。

**职责**:
- 接收用户请求
- 参数验证
- 异步任务调度
- 进度推送
- 响应返回

**接口设计**:
```
POST   /api/v1/projects          # 创建项目
GET    /api/v1/projects/:id      # 获取项目详情
POST   /api/v1/projects/:id/generate  # 开始生成视频
WS     /ws/projects/:id          # 实时进度推送
GET    /api/v1/videos/:id        # 获取视频信息
```

### 3.2 Core 模块 (`backend/src/core`)
核心业务编排逻辑。

**职责**:
- Agent协调和工作流编排
- 进度跟踪和状态上报
- LLM工厂模式管理
- 异常处理

**核心类**:
- `AnimePipeline`: 主工作流编排器，协调四个Agent按顺序执行
- `ProgressTracker`: 进度跟踪器，负责实时上报任务进度
- `LLMFactory`: LLM工厂类，统一管理语言模型的创建
- `PipelineException`: 工作流级别的异常类

**执行流程** (`backend/src/core/pipeline.py`):
```python
class AnimePipeline:
    def __init__(self, api_key, progress_tracker, task_id):
        # 初始化LLM (Claude 4.5 Sonnet)
        self.llm = ChatOpenAI(...)
        
        # 初始化四个Agent
        self.novel_parser = NovelParserAgent(llm=self.llm)
        self.storyboard = StoryboardAgent(llm=self.llm)
        self.scene_renderer = SceneRenderer(task_id=task_id)
        self.scene_composer = SceneComposer(task_id=task_id)
        
        self.progress_tracker = progress_tracker
    
    async def execute(self, novel_text, options):
        # 1. 小说解析 (10-20%)
        novel_result = await self.novel_parser.parse(novel_text)
        
        # 2. 分镜设计 (20-30%)
        storyboard_data = await self.storyboard.create(novel_result.model_dump())
        
        # 3. 场景渲染 (30-70%)
        render_result = await self.scene_renderer.render(storyboard_data)
        
        # 4. 视频合成 (70-100%)
        video_result = await self.scene_composer.compose(render_result)
        
        return video_result
```

**进度跟踪机制**:
- 使用 `ProgressTracker` 在每个阶段更新进度
- 通过 WebSocket 实时推送进度给前端
- 进度区间划分: 解析(0-20%), 分镜(20-30%), 渲染(30-70%), 合成(70-100%)

### 3.3 Agents 模块 (`backend/src/agents`)
四个核心Agent，按顺序执行小说到动漫的完整转换流程。

#### 3.3.1 NovelParserAgent (`novel_parser/`)
**职责**: 解析小说文本，提取结构化数据

**核心功能**:
- 支持两种模式：simple（直接解析）和 enhanced（分块解析长文本）
- 提取角色信息（姓名、外貌、性格、角色定位）
- 提取章节和场景信息
- 识别关键情节点

**工作流程**:
```python
class NovelParserAgent:
    async def parse(self, novel_text: str, mode: str = "enhanced"):
        # 1. 验证输入
        self._validate_input(novel_text)
        
        # 2. 根据模式选择解析策略
        if mode == "enhanced":
            # 分块处理长文本
            chunks = self._split_text_into_chunks(novel_text)
            chunk_results = [await self._parse_chunk(chunk) for chunk in chunks]
            result = self._merge_results(chunk_results)
        else:
            # 直接解析
            result = await self._parse_simple(novel_text)
        
        # 3. 转换为Pydantic模型
        return self._convert_to_model(result)
```

**输出数据结构**:
- `NovelParseResult`: 包含 characters, chapters, plot_points
- `CharacterInfo`: 角色信息（含 appearance, personality, role 等）
- `Chapter`: 章节信息（含多个 scenes）
- `SceneInfo`: 场景信息（location, time, characters, description 等）

**关键配置** (`config.py`):
- `chunk_size`: 分块大小（默认3000字符）
- `max_characters`: 最多提取角色数
- `max_scenes`: 最多提取场景数

#### 3.3.2 StoryboardAgent (`storyboard/`)
**职责**: 将小说解析数据转换为可渲染的分镜脚本

**核心功能**:
- 将 NovelParseResult 转换为 StoryboardResult
- 为每个场景生成图像渲染信息（prompt、风格、镜头角度等）
- 为每个场景生成音频信息（对白或旁白、说话人、预估时长）
- 合并全局角色信息和场景局部角色外貌
- 计算场景时长

**工作流程**:
```python
class StoryboardAgent:
    async def create(self, novel_data: Dict) -> Dict:
        novel_result = NovelParseResult(**novel_data)
        
        storyboard_chapters = []
        for chapter in novel_result.chapters:
            storyboard_scenes = []
            for scene in chapter.scenes:
                # 1. 合并角色信息
                characters = self._merge_character_info(scene, global_characters)
                
                # 2. 生成音频信息
                audio = self._create_audio_info(scene)
                
                # 3. 生成图像渲染信息
                image = self._create_image_info(scene, characters)
                
                # 4. 计算时长
                duration = self._calculate_scene_duration(audio)
                
                storyboard_scene = StoryboardScene(
                    characters=characters,
                    audio=audio,
                    image=image,
                    duration=duration,
                    ...
                )
                storyboard_scenes.append(storyboard_scene)
            
            storyboard_chapters.append(StoryboardChapter(...))
        
        return StoryboardResult(chapters=storyboard_chapters)
```

**输出数据结构**:
- `StoryboardResult`: 包含 chapters, total_duration, total_scenes
- `StoryboardScene`: 场景分镜（包含 image, audio, characters, duration）
- `ImageRenderInfo`: 图像渲染配置（prompt, style_tags, shot_type 等）
- `AudioInfo`: 音频配置（type, speaker, text, estimated_duration）

**关键配置** (`config.py`):
- `min_scene_duration`: 最小场景时长（秒）
- `max_scene_duration`: 最大场景时长（秒）
- `dialogue_chars_per_second`: 对白语速（字符/秒）

#### 3.3.3 SceneRenderer (`scene_renderer/`)
**职责**: 为每个场景生成图片和音频文件

**核心功能**:
- 调用七牛云图像生成API生成场景图片
- 调用七牛云TTS API生成场景音频
- 智能匹配角色声音（根据性别、年龄段选择）
- 支持重试机制和降级策略
- 使用 TaskStorageManager 管理文件存储

**工作流程**:
```python
class SceneRenderer:
    async def render(self, storyboard: StoryboardResult) -> RenderResult:
        # 1. 验证输入
        self._validate_storyboard(storyboard)
        
        # 2. 预分配角色声音
        self._prepare_character_voices(storyboard)
        
        # 3. 渲染所有章节
        rendered_chapters = []
        for chapter in storyboard.chapters:
            rendered_scenes = []
            for scene in chapter.scenes:
                # 3.1 生成图片
                image_path = await self._generate_image(scene)
                
                # 3.2 生成音频
                audio_path = await self._generate_audio(scene)
                
                # 3.3 获取音频时长
                audio_duration = await self._get_audio_duration(audio_path)
                
                rendered_scene = RenderedScene(
                    image_path=image_path,
                    audio_path=audio_path,
                    duration=max(scene.duration, audio_duration),
                    ...
                )
                rendered_scenes.append(rendered_scene)
            
            rendered_chapters.append(RenderedChapter(...))
        
        return RenderResult(chapters=rendered_chapters)
```

**声音匹配策略**:
- 维护28种不同的七牛云声音类型（不同性别、年龄段）
- 根据角色的 gender 和 age_stage 自动匹配最佳声音
- 使用 `character_voice_cache` 确保同一角色声音一致

**输出数据结构**:
- `RenderResult`: 包含 chapters, total_duration, total_scenes, output_directory
- `RenderedChapter`: 渲染后的章节
- `RenderedScene`: 包含 image_path, audio_path, duration, metadata

**关键配置** (`config.py`):
- `qiniu_api_key`: 七牛云API密钥
- `image_model`: 图像生成模型
- `image_size`: 图像尺寸（如 "1024x1024"）
- `retry_attempts`: 重试次数

#### 3.3.4 SceneComposer (`scene_composer/`)
**职责**: 将渲染的场景合成为最终视频

**核心功能**:
- 使用FFmpeg将图片+音频合成为场景视频
- 拼接多个场景视频为章节视频
- 拼接多个章节视频为最终视频
- 自动清理临时文件
- 将最终视频持久化到指定目录

**工作流程**:
```python
class SceneComposer:
    async def compose(self, render_result: RenderResult) -> Dict:
        # 1. 验证输入
        self._validate_input(render_result)
        
        # 2. 合成每个章节
        chapter_videos = []
        for chapter in render_result.chapters:
            # 2.1 合成章节中的每个场景
            scene_videos = []
            for scene in chapter.scenes:
                scene_video = await self._compose_scene(scene)
                scene_videos.append(scene_video)
            
            # 2.2 拼接场景为章节视频
            chapter_video = await self._concatenate_videos(
                scene_videos, f"chapter_{chapter.chapter_id}"
            )
            chapter_videos.append(chapter_video)
        
        # 3. 拼接章节为最终视频
        if len(chapter_videos) == 1:
            final_video = chapter_videos[0]
        else:
            final_video = await self._concatenate_videos(
                chapter_videos, "final_video"
            )
        
        # 4. 持久化最终视频
        final_path = self._persist_final_video(final_video)
        
        return {
            "video_path": final_path,
            "duration": await self._get_video_duration(final_path),
            "file_size": os.path.getsize(final_path),
            ...
        }
```

**FFmpeg命令构建**:
- 场景合成: 静态图片循环 + 音频 → 场景视频
- 视频拼接: 使用 concat demuxer 无损拼接

**输出结构**:
- 返回字典包含: video_path, duration, file_size, total_scenes, total_chapters

**关键配置** (`config.py`):
- `codec`: 视频编码器（默认 "libx264"）
- `preset`: 编码预设（默认 "medium"）
- `audio_codec`: 音频编码器（默认 "aac"）
- `timeout`: FFmpeg超时时间

#### 3.3.5 Base模块 (`base/`)
为所有Agent提供基础能力:

- `TaskStorageManager`: 统一的文件存储管理（图片、音频、临时文件）
- `llm_utils.py`: LLM调用工具函数（call_llm_json 等）
- `exceptions.py`: 自定义异常类（ValidationError, ParseError, APIError 等）
- `agent.py`: Agent基类（如需要）
- `download_utils.py`: 文件下载工具

### 3.4 Services 模块 (`backend/src/services`)
外部服务集成。

**职责**:
- LLM API调用
- 图像生成API调用
- TTS API调用
- 对象存储操作
- 缓存操作

### 3.5 Models 模块 (`backend/src/models`)
数据模型定义。

**主要模型**:
- `Project`: 项目信息
- `Character`: 角色信息
- `Scene`: 场景信息
- `Video`: 视频信息
- `Task`: 任务信息

### 3.6 Utils 模块 (`backend/src/utils`)
工具函数。

**包含**:
- 日志工具
- 配置加载
- 文件处理
- 时间处理
- 异常定义

## 4. 数据模型

### 4.1 关系数据库 (PostgreSQL)

```sql
-- 项目表
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    novel_text TEXT NOT NULL,
    status VARCHAR(20),  -- pending/processing/completed/failed
    progress INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 角色表
CREATE TABLE characters (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    name VARCHAR(100),
    description TEXT,
    reference_image_url TEXT,
    features JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 场景表
CREATE TABLE scenes (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    scene_number INT,
    description TEXT,
    image_url TEXT,
    audio_url TEXT,
    duration FLOAT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 视频表
CREATE TABLE videos (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    video_url TEXT,
    thumbnail_url TEXT,
    duration FLOAT,
    file_size BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.2 缓存策略 (Redis)

```
# LLM响应缓存
llm:{model}:{hash(prompt)} → response (TTL: 24h)

# 角色特征缓存
character:{project_id}:{character_name} → features (TTL: 7d)

# 任务进度缓存
task:progress:{task_id} → progress_data (TTL: 1h)
```

### 4.3 向量数据库 (Chroma)

用于角色语义检索和场景相似度匹配。

## 5. 核心工作流

### 5.1 完整的视频生成流程

基于 `backend/src/core/pipeline.py` 的实际实现：

```python
class AnimePipeline:
    async def execute(self, novel_text: str, options=None) -> Dict[str, Any]:
        """
        完整的动漫生成流程，分为四个阶段
        """
        
        # ========== 阶段1: 小说解析 (进度: 0% → 20%) ==========
        logger.info("1. 开始解析小说...")
        await self.progress_tracker.update(self.id, "novel_parsing", 10, "小说解析中")
        
        # 调用 NovelParserAgent.parse()
        # 输入: 小说文本
        # 输出: NovelParseResult (characters, chapters, plot_points)
        novel_result = await self.novel_parser.parse(novel_text)
        
        await self.progress_tracker.update(self.id, "scene_extraction", 20, "场景提取中")
        logger.info("小说解析完成")
        
        # ========== 阶段2: 分镜设计 (进度: 20% → 30%) ==========
        logger.info("2. 开始分镜设计...")
        
        # 调用 StoryboardAgent.create()
        # 输入: NovelParseResult (转为字典)
        # 输出: StoryboardResult (chapters with scenes, audio, image info)
        novel_data_dict = novel_result.model_dump()
        storyboard_data = await self.storyboard.create(novel_data_dict)
        
        await self.progress_tracker.update(self.id, "scene_extraction", 30, "场景提取完成")
        logger.info("分镜设计完成")
        
        # ========== 阶段3: 场景渲染 (进度: 30% → 70%) ==========
        logger.info("3. 开始渲染场景（生成图片和音频）...")
        await self.progress_tracker.update(self.id, "scene_rendering", 40, "场景渲染中")
        
        # 调用 SceneRenderer.render()
        # 输入: StoryboardResult
        # 输出: RenderResult (chapters with rendered scenes, image_path, audio_path)
        storyboard_result = StoryboardResult(**storyboard_data)
        render_result = await self.scene_renderer.render(storyboard_result)
        
        await self.progress_tracker.update(self.id, "scene_rendering", 70, "场景渲染完成")
        logger.info(f"场景渲染完成: {render_result.total_scenes} 个场景")
        
        # ========== 阶段4: 视频合成 (进度: 70% → 100%) ==========
        logger.info("4. 开始合成视频...")
        await self.progress_tracker.update(self.id, "video_composition", 80, "视频合成中")
        
        # 调用 SceneComposer.compose()
        # 输入: RenderResult
        # 输出: Dict (video_path, duration, file_size, etc.)
        video_result = await self.scene_composer.compose(render_result)
        
        await self.progress_tracker.update(self.id, "video_composition", 100, "视频合成完成")
        logger.info(f"视频合成完成: {video_result.get('video_path', '')}")
        
        # ========== 返回最终结果 ==========
        return {
            "video_path": video_result.get("video_path", ""),
            "thumbnail_url": video_result.get("thumbnail_url", ""),
            "duration": video_result.get("duration", 0.0),
            "file_size": video_result.get("file_size", 0),
            "scenes_count": render_result.total_scenes
        }
```

### 5.2 数据流转示意图

```
小说文本 (str)
    ↓
[NovelParserAgent.parse()]
    ↓
NovelParseResult
├── characters: List[CharacterInfo]
├── chapters: List[Chapter]
│   └── scenes: List[SceneInfo]
└── plot_points: List[PlotPoint]
    ↓
[StoryboardAgent.create()]
    ↓
StoryboardResult
└── chapters: List[StoryboardChapter]
    └── scenes: List[StoryboardScene]
        ├── image: ImageRenderInfo (prompt, style, etc.)
        ├── audio: AudioInfo (text, speaker, type)
        ├── characters: List[CharacterRenderInfo]
        └── duration: float
    ↓
[SceneRenderer.render()]
    ↓
RenderResult
└── chapters: List[RenderedChapter]
    └── scenes: List[RenderedScene]
        ├── image_path: str (PNG文件路径)
        ├── audio_path: str (MP3文件路径)
        ├── duration: float
        └── metadata: Dict
    ↓
[SceneComposer.compose()]
    ↓
最终视频 (MP4)
├── video_path: str
├── duration: float
├── file_size: int
└── scenes_count: int
```

### 5.2 错误处理策略

```python
# 重试机制
@retry(max_attempts=3, backoff=exponential)
async def call_api():
    pass

# 降级策略
async def generate_image(prompt: str):
    try:
        return await dalle3_api.generate(prompt)
    except APIError:
        # 降级到备用模型
        return await sd_api.generate(prompt)
```

## 6. 接口设计

### 6.1 RESTful API

#### 创建项目
```http
POST /api/v1/projects
Content-Type: application/json

{
  "novel_text": "小说内容...",
  "options": {
    "style": "anime",
    "quality": "standard"
  }
}

Response 201:
{
  "project_id": "uuid",
  "status": "pending",
  "created_at": "2024-10-24T12:00:00Z"
}
```

#### 开始生成
```http
POST /api/v1/projects/{project_id}/generate

Response 202:
{
  "task_id": "uuid",
  "status": "processing",
  "estimated_time": 600
}
```

#### 获取项目状态
```http
GET /api/v1/projects/{project_id}

Response 200:
{
  "project_id": "uuid",
  "status": "processing",
  "progress": 45,
  "current_stage": "image_generation",
  "video_url": null
}
```

### 6.2 WebSocket API

```javascript
// 连接
ws://api.example.com/ws/projects/{project_id}

// 接收消息
{
  "type": "progress",
  "stage": "image_generation",
  "progress": 45,
  "message": "正在生成第15个场景..."
}

{
  "type": "completed",
  "video_url": "https://cdn.example.com/videos/xxx.mp4",
  "duration": 300
}

{
  "type": "error",
  "error": "API调用失败",
  "details": "..."
}
```

## 7. 部署架构

### 7.1 开发环境

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7
    volumes:
      - redis_data:/data
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
```

### 7.2 生产环境

- **负载均衡**: Nginx
- **应用服务器**: Gunicorn + Uvicorn
- **数据库**: PostgreSQL (主从复制)
- **缓存**: Redis Cluster
- **对象存储**: 七牛云
- **监控**: Prometheus + Grafana
- **日志**: ELK Stack

## 8. 性能优化

### 8.1 并发处理
- 使用asyncio进行异步IO
- 批量生成图片和音频
- 连接池管理

### 8.2 缓存策略
- LLM响应缓存
- 角色特征缓存
- CDN缓存静态资源

### 8.3 成本优化
- 使用开源模型降低成本
- 缓存减少重复调用
- 批量请求获取折扣

## 9. 监控与可观测性

### 9.1 日志
- 结构化日志 (structlog)
- 日志级别: DEBUG/INFO/WARNING/ERROR
- 日志存储: ELK Stack

### 9.2 指标
- API响应时间
- 任务处理时长
- API调用成本
- 错误率

### 9.3 告警
- API错误率告警
- 任务失败告警
- 资源使用告警

## 10. 安全性

### 10.1 认证授权
- JWT Token认证
- API Key管理
- 权限控制

### 10.2 数据安全
- 敏感数据加密
- API Key加密存储
- HTTPS通信

### 10.3 限流保护
- 用户级别限流
- IP级别限流
- API调用限流

## 11. 测试策略

### 11.1 单元测试
- Agent单元测试
- Service单元测试
- 覆盖率 > 80%

### 11.2 集成测试
- API接口测试
- Agent协作测试
- 端到端测试

### 11.3 性能测试
- 压力测试
- 并发测试
- 成本测试

## 12. 开发规范

### 12.1 代码规范
- Python: PEP 8
- TypeScript: ESLint + Prettier
- Git Commit: Conventional Commits

### 12.2 文档规范
- 每个模块必须有DESIGN.md
- 每个函数必须有docstring
- API必须有OpenAPI文档

### 12.3 版本控制
- 主分支: main
- 开发分支: develop
- 功能分支: feature/*
- 修复分支: fix/*

## 13. 项目里程碑

### Phase 1 (3天 - MVP)
- ✅ 基础架构搭建
- ✅ 6个Agent实现
- ✅ 图配文+声音视频生成
- ✅ 简单前端界面

### Phase 2 (1周)
- 引入Celery异步任务
- 优化角色一致性 (SD + IPAdapter)
- 添加转场效果
- 完善监控体系

### Phase 3 (2周)
- 支持图生视频
- 添加背景音乐
- 多语言支持
- 性能优化

## 14. 风险与挑战

### 14.1 技术风险
- **角色一致性**: 目前方案只能达到70-80%一致性
- **API成本**: 需要严格控制调用成本
- **生成速度**: 单个视频需要10-20分钟

### 14.2 缓解措施
- 准备多个角色一致性备选方案
- 实现缓存降低重复调用
- 异步处理提升用户体验

## 15. 参考资料

- FastAPI文档: https://fastapi.tiangolo.com/
- OpenAI API文档: https://platform.openai.com/docs
- Stable Diffusion文档: https://github.com/Stability-AI/stablediffusion
- FFmpeg文档: https://ffmpeg.org/documentation.html
