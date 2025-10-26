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
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 小说解析Agent  │→ │  分镜Agent    │→ │角色一致性Agent │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                           ↓                 │
│                          ┌────────────────┴────────────┐    │
│                          ↓                             ↓    │
│                  ┌──────────────┐            ┌──────────────┐│
│                  │ 图像生成Agent  │            │ 语音合成Agent  ││
│                  └──────────────┘            └──────────────┘│
│                          ↓                             ↓    │
│                          └────────────────┬────────────┘    │
│                                           ↓                 │
│                                  ┌──────────────┐           │
│                                  │ 视频合成Agent  │           │
│                                  └──────────────┘           │
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
- Agent协调
- 工作流管理
- 错误处理
- 重试机制

**核心类**:
- `AnimePipeline`: 主工作流编排器
- `TaskManager`: 任务管理器
- `ProgressTracker`: 进度跟踪器

### 3.3 Agents 模块 (`backend/src/agents`)
四个核心模块，负责小说到动漫的完整转换流程:

1. **NovelParserAgent** (`novel_parser/`): 小说文本解析，提取角色、场景和情节
2. **StoryboardAgent** (`storyboard/`): 分镜脚本设计，将小说数据转换为分镜场景
3. **SceneRenderer** (`scene_renderer/`): 场景渲染，为每个场景生成图片和音频
4. **SceneComposer** (`scene_composer/`): 场景合成，将渲染的场景组合成最终视频

详见各模块目录下的DESIGN.md文档。

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

### 5.1 视频生成流程

```python
async def generate_anime_video(novel_text: str) -> Video:
    # 1. 小说解析
    novel_result = await novel_parser_agent.parse(novel_text)
    # 提取: 角色列表, 章节列表, 场景列表
    
    # 2. 分镜设计
    storyboard_data = await storyboard_agent.create(novel_result)
    # 生成: StoryboardResult (包含渲染所需的完整场景信息)
    
    # 3. 场景渲染
    render_result = await scene_renderer.render(storyboard_data)
    # 为每个场景生成图片和音频，返回 RenderResult
    
    # 4. 视频合成
    video_result = await scene_composer.execute(render_result)
    # 将所有渲染的场景合成为最终视频
    
    return video_result
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
