# 智能动漫生成系统 - 前端

基于 React 18 + TypeScript + Vite + Ant Design 构建的现代化前端应用。

## 功能特性

- 📝 小说文本输入和配置
- 🎬 实时生成进度跟踪（WebSocket）
- 🎥 视频预览和播放
- 👤 角色列表和信息展示
- 🎞️ 场景列表和详情查看
- 📱 响应式设计，支持移动端

## 技术栈

- **框架**: React 18
- **语言**: TypeScript
- **构建工具**: Vite
- **UI库**: Ant Design 5
- **路由**: React Router 6
- **HTTP客户端**: Axios
- **实时通信**: WebSocket

## 快速开始

### 安装依赖

```bash
npm install
```

### 配置环境变量

复制 `.env.example` 到 `.env` 并根据实际情况修改：

```bash
cp .env.example .env
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API 客户端
│   │   └── client.ts     # API 请求封装
│   ├── components/       # 可复用组件
│   │   ├── MainLayout.tsx
│   │   ├── NovelInput.tsx
│   │   ├── ProgressTracker.tsx
│   │   └── VideoPlayer.tsx
│   ├── hooks/            # 自定义 Hooks
│   │   └── useWebSocket.ts
│   ├── pages/            # 页面组件
│   │   ├── HomePage.tsx
│   │   └── ProjectDetailPage.tsx
│   ├── types/            # TypeScript 类型定义
│   │   └── index.ts
│   ├── App.tsx           # 应用根组件
│   ├── main.tsx          # 应用入口
│   └── index.css         # 全局样式
├── index.html            # HTML 模板
├── package.json          # 项目配置
├── tsconfig.json         # TypeScript 配置
├── vite.config.ts        # Vite 配置
└── README.md             # 项目文档
```

## 主要功能模块

### 1. 首页（HomePage）

- 展示系统介绍和特性
- 提供小说文本输入表单
- 配置生成选项（风格、质量）
- 提交后跳转到项目详情页

### 2. 项目详情页（ProjectDetailPage）

- 实时显示生成进度
- WebSocket 连接获取实时更新
- 视频播放器
- 角色和场景信息展示
- 项目数据查看

### 3. 实时进度跟踪

使用 WebSocket 实现：
- 连接到 `/ws/projects/:projectId`
- 接收进度更新消息
- 自动更新UI状态
- 生成完成或失败的通知

### 4. API 集成

所有API请求通过 `src/api/client.ts` 统一管理：
- 项目创建和查询
- 视频生成触发
- 角色和场景数据获取

## 开发规范

### 代码风格

- 使用 ESLint 和 TypeScript 进行代码检查
- 遵循 React Hooks 最佳实践
- 组件使用函数式组件
- 使用 TypeScript 进行类型检查

### Git Commit 规范

遵循 Conventional Commits:
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

## API 接口说明

### 创建项目
```
POST /api/v1/projects
Body: { novel_text: string, options?: { style?: string, quality?: string } }
```

### 获取项目详情
```
GET /api/v1/projects/:projectId
```

### 开始生成视频
```
POST /api/v1/projects/:projectId/generate
```

### WebSocket 连接
```
WS /ws/projects/:projectId
```

## 浏览器支持

- Chrome >= 90
- Firefox >= 88
- Safari >= 14
- Edge >= 90

## 许可证

MIT
