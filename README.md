# 智能动漫生成系统 (Hackathon)

基于 AI 的智能动漫生成系统，可以将小说文本自动转换为动漫视频。

## 快速开始

### 1. 环境准备

运行自动化环境准备脚本：

```bash
chmod +x setup.sh
./setup.sh
```

该脚本会自动：
- 检查系统依赖（Python 3.10+, Node.js 16+, Redis）
- 创建并配置后端 Python 虚拟环境
- 安装后端 Python 依赖
- 安装前端 Node.js 依赖
- 创建配置文件

### 2. 配置 API 密钥

编辑 `backend/.env` 文件，填入你的 OpenAI API 密钥：

```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 3. 环境检查

运行环境检查工具，确保所有依赖已正确安装：

```bash
chmod +x check-env.sh
./check-env.sh
```

### 4. 启动服务

#### 方式一：使用 Makefile（推荐）

```bash
make help        # 查看所有可用命令

make backend     # 启动后端服务
make frontend    # 启动前端服务（新终端）
make test        # 运行测试
```

#### 方式二：手动启动

**后端：**
```bash
cd backend
source venv/bin/activate
pytest  # 运行测试
```

**前端：**
```bash
cd frontend
npm run dev
```

#### 方式三：使用 Docker（完整环境）

```bash
cp .env.example .env  # 配置环境变量
make docker-up        # 启动所有服务（后端、前端、PostgreSQL、Redis）
make docker-logs      # 查看日志
make docker-down      # 停止服务
```

## 项目结构

```
hackathon/
├── backend/              # 后端服务 (Python/FastAPI)
│   ├── src/
│   │   ├── agents/      # AI Agent 模块
│   │   ├── api/         # API 接口
│   │   ├── core/        # 核心业务逻辑
│   │   ├── models/      # 数据模型
│   │   └── services/    # 外部服务集成
│   ├── tests/           # 测试文件
│   ├── requirements.txt # Python 依赖
│   ├── Dockerfile       # Docker 配置
│   └── README.md        # 后端文档
├── frontend/            # 前端服务 (React/TypeScript)
│   ├── src/
│   │   ├── components/  # UI 组件
│   │   ├── pages/       # 页面
│   │   ├── api/         # API 客户端
│   │   └── types/       # 类型定义
│   ├── package.json     # Node.js 依赖
│   ├── Dockerfile       # Docker 配置
│   └── README.md        # 前端文档
├── docker-compose.yml   # Docker Compose 配置
├── setup.sh             # 环境准备脚本
├── check-env.sh         # 环境检查脚本
├── Makefile             # 开发命令
├── DESIGN.md            # 架构设计文档
└── README.md            # 项目文档（本文件）
```

## 系统依赖

### 必需

- **Python**: 3.10+ (后端开发)
- **Node.js**: 16+ (前端开发)
- **npm**: 8+ (包管理)

### 可选

- **Redis**: 7+ (缓存，可选但推荐)
- **Docker**: 20+ (容器化部署)
- **Docker Compose**: 2+ (多容器编排)

### API 依赖

- **OpenAI API**: 需要有效的 API 密钥

## 开发命令

所有命令都可以通过 Makefile 运行：

```bash
# 环境相关
make setup              # 初始化开发环境
make install            # 安装依赖
make clean              # 清理临时文件

# 开发运行
make backend            # 启动后端
make frontend           # 启动前端

# 测试和检查
make test               # 运行所有测试
make test-backend       # 运行后端测试
make lint               # 代码检查

# Docker 相关
make docker-up          # 启动 Docker 服务
make docker-down        # 停止 Docker 服务
make docker-logs        # 查看日志
make docker-clean       # 清理 Docker 资源
```

## 核心功能

- 📝 小说文本解析
- 🎭 角色一致性管理
- 🎬 智能分镜设计
- 🖼️ AI 图像生成
- 🔊 语音合成
- 🎥 视频合成
- 🌐 实时进度跟踪（WebSocket）

## 技术栈

### 后端
- FastAPI (Python 3.10+)
- LangChain (AI 编排)
- OpenAI API (LLM + 图像生成 + TTS)
- SQLAlchemy (ORM)
- PostgreSQL (数据库)
- Redis (缓存)

### 前端
- React 18 + TypeScript
- Vite (构建工具)
- Ant Design (UI 库)
- Axios (HTTP 客户端)
- WebSocket (实时通信)

### 基础设施
- Docker + Docker Compose
- GitHub Actions (CI/CD)

## 文档

- [DESIGN.md](./DESIGN.md) - 详细架构设计
- [backend/README.md](./backend/README.md) - 后端开发文档
- [frontend/README.md](./frontend/README.md) - 前端开发文档
- [OPTIMIZATIONS.md](./backend/OPTIMIZATIONS.md) - 架构优化记录
- [REFACTORING.md](./backend/REFACTORING.md) - 重构记录

## 故障排除

### 问题：Python 版本过低

```bash
# 安装 Python 3.10+
# macOS
brew install python@3.10

# Ubuntu
sudo apt-get install python3.10
```

### 问题：Redis 连接失败

```bash
# 启动 Redis
redis-server

# 或使用 Docker
docker run -d -p 6379:6379 redis:7
```

### 问题：npm 安装失败

```bash
# 清理缓存并重新安装
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### 问题：Docker 启动失败

```bash
# 检查 .env 文件是否存在
cp .env.example .env

# 编辑 .env 填入配置
vim .env

# 重新启动
docker-compose up -d
```

## 许可证

MIT

## 联系方式

如有问题，请提交 Issue。
