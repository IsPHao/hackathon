# 智能动漫生成系统

一个基于AI的端到端动漫视频生成平台，能够将小说文本自动转换为完整的动漫视频。

## 项目概述

本项目是一个智能动漫生成系统，通过AI Agent工作流将小说文本转换为动漫视频。系统采用四阶段流水线架构：

### 核心Agent流程

1. **NovelParserAgent** - 小说文本解析
   - 提取角色信息（姓名、外貌、性格、角色定位）
   - 提取章节和场景信息
   - 识别关键情节点
   - 支持增强模式（分块处理长文本）

2. **StoryboardAgent** - 分镜脚本设计
   - 将解析结果转换为可渲染的分镜脚本
   - 生成图像渲染信息（prompt、风格、镜头角度）
   - 生成音频信息（对白/旁白、说话人、时长）
   - 合并全局角色信息和场景角色外貌

3. **SceneRenderer** - 场景渲染（图片+音频）
   - 调用七牛云图像生成API生成场景图片
   - 调用七牛云TTS API生成角色对话音频
   - 智能匹配角色声音（28种不同声音类型）
   - 支持重试机制和降级策略

4. **SceneComposer** - 视频合成
   - 使用FFmpeg将图片+音频合成场景视频
   - 拼接场景为章节视频
   - 合成最终完整视频（MP4格式）
   - 自动清理临时文件

## 技术架构

### 后端技术栈
- **框架**: FastAPI (Python 3.10+) + Uvicorn
- **异步处理**: asyncio, FastAPI BackgroundTasks
- **AI模型**: Claude 3.5 Sonnet (via 七牛云API)
- **图像生成**: 七牛云 Image Generation API (Qwen-Image/WanX系列)
- **语音合成**: 七牛云 TTS API
- **视频处理**: FFmpeg
- **数据模型**: Pydantic 2.0+

### 前端技术栈
- **框架**: React + TypeScript
- **通信**: RESTful API + WebSocket (实时进度推送)

### 基础设施
- **对象存储**: 七牛云
- **本地存储**: 任务级别文件管理（TaskStorageManager）

## 系统架构

### 目录结构

```
backend/
├── src/
│   ├── agents/           # AI Agent实现
│   │   ├── base/        # 基础工具（存储管理、异常处理）
│   │   ├── novel_parser/     # 小说解析Agent
│   │   ├── storyboard/       # 分镜设计Agent
│   │   ├── scene_renderer/   # 场景渲染Agent
│   │   └── scene_composer/   # 视频合成Agent
│   ├── core/            # 核心业务逻辑
│   │   ├── pipeline.py       # AnimePipeline工作流编排
│   │   ├── llm_factory.py    # LLM工厂模式管理
│   │   └── progress_tracker.py  # 进度跟踪
│   ├── api/             # FastAPI接口
│   │   ├── app.py       # FastAPI应用
│   │   ├── routes.py    # API路由
│   │   └── schemas.py   # 请求/响应模型
│   ├── models/          # 数据模型（数据库ORM）
│   └── services/        # 外部服务集成
├── tests/               # 测试用例
└── requirements.txt     # Python依赖

frontend/
├── src/
│   ├── components/      # React组件
│   ├── pages/           # 页面
│   └── api/             # API调用
└── package.json
```

### 核心工作流（AnimePipeline）

系统通过 `AnimePipeline` 编排四个Agent按顺序执行：

```
小说文本 (str)
    ↓ [0-20%: 小说解析]
NovelParseResult (characters, chapters, scenes)
    ↓ [20-30%: 分镜设计]
StoryboardResult (scenes with image/audio info)
    ↓ [30-70%: 场景渲染]
RenderResult (image_path + audio_path for each scene)
    ↓ [70-100%: 视频合成]
最终视频 (MP4)
```

### 数据模型流转

1. **NovelParseResult**: 包含 `characters`, `chapters`, `plot_points`
2. **StoryboardResult**: 包含 `chapters` (每个场景带 `ImageRenderInfo` 和 `AudioInfo`)
3. **RenderResult**: 包含 `chapters` (每个场景带 `image_path` 和 `audio_path`)
4. **最终输出**: `video_path`, `duration`, `file_size`, `scenes_count`

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 16+
- FFmpeg (用于视频合成)
- 七牛云API Key (用于图像生成和语音合成)

### 配置说明

需要配置以下环境变量或配置文件：

```bash
# 七牛云配置
QINIU_API_KEY=your_api_key

# 图像生成配置
IMAGE_MODEL=qwen-image-plus
IMAGE_SIZE=1024x1024

# 语音合成配置
# 系统支持28种声音类型，自动根据角色性别和年龄段匹配
# 例如：qiniu_zh_female_wwxkjx (女性)、qiniu_zh_male_wugeda (男性)
```

### 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动API服务器
python run_server.py

# 或使用uvicorn直接启动
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

API服务将运行在 `http://localhost:8000`

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将运行在 `http://localhost:3000`

## API接口

### RESTful API

```
POST /api/v1/projects          # 创建项目
GET  /api/v1/projects/:id      # 获取项目详情
POST /api/v1/projects/:id/generate  # 开始生成视频
GET  /api/v1/videos/:id        # 获取视频信息
```

### WebSocket

```
WS /ws/projects/:id            # 实时进度推送
```

实时接收生成进度：
```json
{
  "type": "progress",
  "stage": "scene_rendering",
  "progress": 45,
  "message": "正在渲染第15个场景..."
}
```

详细的API文档请查看 `backend/README_API.md`

## 测试

运行测试：

```bash
cd backend

# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/agents/novel_parser/ -v
pytest tests/core/test_pipeline.py -v

# 运行测试并显示覆盖率
pytest tests/ --cov=src --cov-report=html
```

## 进一步了解

- **完整架构设计**: 查看 `DESIGN.md` 了解详细的系统架构和设计理念
- **核心模块文档**: 
  - `backend/src/core/DESIGN.md` - 核心业务逻辑设计
  - `backend/src/core/README.md` - Core模块使用说明
  - `backend/src/api/DESIGN.md` - API层设计
- **Agent实现细节**: 各Agent目录下有独立的文档说明

## 贡献指南

欢迎提交Issue和Pull Request来改进项目！

### 开发规范

- Python代码遵循 PEP 8 规范
- TypeScript代码使用 ESLint + Prettier
- Git提交信息遵循 Conventional Commits
- 所有新功能需要添加相应的单元测试

## 许可证

MIT License