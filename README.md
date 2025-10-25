# 智能动漫生成系统

一个基于 AI 的智能动漫生成系统，能够自动将小说文本转换为动漫视频，支持角色一致性、多模态输出（图配文+声音）。

## 🚀 快速开始

### 方式 1: 使用自动化脚本（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/IsPHao/hackathon.git
cd hackathon

# 2. 检查环境
./check-env.sh

# 3. 自动设置环境
./setup.sh

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置必要的 API keys

# 5. 使用 Docker 启动完整环境（推荐）
docker-compose up -d

# 或使用 Makefile
make docker-up
```

### 方式 2: 使用 Docker（最简单）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 OPENAI_API_KEY 等

# 2. 启动所有服务
docker-compose up -d

# 3. 访问应用
# - 前端: http://localhost:3000
# - 后端: http://localhost:8000
# - API 文档: http://localhost:8000/docs
```

### 方式 3: 手动设置

#### 前置要求
- Python >= 3.10
- Node.js >= 18
- Redis (可选，用于缓存)
- PostgreSQL (可选，用于数据存储)

#### 后端设置

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 运行测试
pytest

# 启动服务
uvicorn main:app --reload
```

#### 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 📋 环境检查

运行环境检查脚本来验证所有依赖是否正确安装：

```bash
./check-env.sh
```

该脚本会检查：
- ✅ Python 版本 (>= 3.10)
- ✅ Node.js 版本 (>= 18)
- ✅ npm 版本
- ✅ Git
- ✅ Docker 和 Docker Compose（可选）
- ✅ Redis 和 PostgreSQL（可选）
- ✅ 环境配置文件

## 🛠️ 开发命令

项目提供了 Makefile 来简化常用命令：

```bash
make help          # 显示所有可用命令
make check         # 检查环境依赖
make setup         # 自动设置开发环境
make install       # 安装所有依赖
make test          # 运行测试
make lint          # 运行代码检查
make clean         # 清理临时文件

# Docker 相关
make docker-up     # 启动所有 Docker 服务
make docker-down   # 停止所有 Docker 服务
make docker-logs   # 查看 Docker 日志
make docker-ps     # 查看运行中的容器
```

## 🏗️ 项目结构

```
hackathon/
├── backend/              # Python 后端
│   ├── src/
│   │   ├── agents/       # AI Agent 模块
│   │   ├── api/          # API 接口
│   │   ├── core/         # 核心业务逻辑
│   │   ├── models/       # 数据模型
│   │   └── services/     # 外部服务集成
│   ├── tests/            # 测试文件
│   ├── Dockerfile        # 后端 Docker 镜像
│   └── requirements.txt  # Python 依赖
├── frontend/             # React 前端
│   ├── src/
│   │   ├── api/          # API 客户端
│   │   ├── components/   # UI 组件
│   │   ├── hooks/        # React Hooks
│   │   ├── pages/        # 页面组件
│   │   └── types/        # TypeScript 类型
│   ├── Dockerfile        # 前端 Docker 镜像
│   └── package.json      # Node.js 依赖
├── scripts/              # 工具脚本
│   └── init-db.sql       # 数据库初始化
├── docker-compose.yml    # Docker 编排配置
├── check-env.sh          # 环境检查脚本
├── setup.sh              # 自动设置脚本
├── Makefile              # 开发命令
├── .env.example          # 环境变量模板
├── .python-version       # Python 版本要求
└── DESIGN.md             # 架构设计文档
```

## 🔧 配置说明

### 环境变量

项目使用环境变量进行配置。主要配置项包括：

**根目录 `.env`**
```bash
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1

# 数据库
DATABASE_URL=postgresql://anime_user:anime_password@localhost:5432/anime_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# 应用配置
LOG_LEVEL=INFO
ENVIRONMENT=development
```

**后端 `backend/.env`**
```bash
# LLM 配置
DEFAULT_MODEL=gpt-4o-mini
DEFAULT_TEMPERATURE=0.3
```

**前端 `frontend/.env`**
```bash
# API 配置
VITE_API_BASE_URL=/api/v1
VITE_WS_BASE_URL=ws://localhost:8000
```

### Docker 服务

使用 Docker Compose 会自动启动以下服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存 |
| Backend | 8000 | 后端 API |
| Frontend | 3000 | 前端应用 |

## 📚 主要功能

- 📝 **小说解析**: 自动解析小说文本，提取角色、场景和情节
- 🎬 **分镜设计**: 智能生成分镜脚本和场景描述
- 👤 **角色一致性**: 保持角色在整个动漫中的视觉一致性
- 🖼️ **图像生成**: 基于场景描述生成高质量动漫图像
- 🔊 **语音合成**: 为对话生成自然的语音
- 🎥 **视频合成**: 将图片、音频合成为完整视频

## 🧪 测试

```bash
# 运行后端测试
cd backend
source venv/bin/activate
pytest

# 运行前端测试（如果有）
cd frontend
npm test
```

## 📖 API 文档

后端服务启动后，可以访问自动生成的 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔍 故障排查

### 常见问题

**1. Python 版本不匹配**
```bash
# 使用 pyenv 安装正确的 Python 版本
pyenv install 3.11
pyenv local 3.11
```

**2. Node.js 版本不匹配**
```bash
# 使用 nvm 安装正确的 Node.js 版本
nvm install 18
nvm use 18
```

**3. Docker 服务启动失败**
```bash
# 查看日志
docker-compose logs

# 重新构建镜像
docker-compose up -d --build
```

**4. 依赖安装失败**
```bash
# 清理缓存后重新安装
make clean
make install
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

MIT License

## 📞 联系方式

- 项目地址: https://github.com/IsPHao/hackathon
- 问题反馈: https://github.com/IsPHao/hackathon/issues

## 🙏 致谢

- OpenAI - GPT 和 DALL-E API
- LangChain - AI 应用开发框架
- FastAPI - 现代化 Python Web 框架
- React - 用户界面库
- Ant Design - 企业级 UI 设计

---

更多详细的架构设计和技术文档，请查看 [DESIGN.md](./DESIGN.md)