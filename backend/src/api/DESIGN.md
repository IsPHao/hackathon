# API 模块设计文档

## 1. 模块概述

API模块是系统的HTTP接口层，负责接收客户端请求、参数验证、任务调度和响应返回。

### 1.1 职责
- 提供RESTful API接口
- WebSocket实时通信
- 请求参数验证
- 异步任务调度
- 认证授权
- 限流保护
- 错误处理

### 1.2 技术栈
- FastAPI
- Pydantic (数据验证)
- Python-Jose (JWT)
- Slowapi (限流)

## 2. 目录结构

```
api/
├── __init__.py
├── routes/
│   ├── __init__.py
│   ├── projects.py      # 项目相关接口
│   ├── videos.py        # 视频相关接口
│   └── websocket.py     # WebSocket接口
├── schemas/
│   ├── __init__.py
│   ├── project.py       # 项目数据模型
│   ├── video.py         # 视频数据模型
│   └── common.py        # 通用数据模型
├── dependencies.py      # 依赖注入
├── middleware.py        # 中间件
└── app.py              # FastAPI应用实例
```

## 3. 接口设计

### 3.1 项目管理接口

#### 创建项目
```python
@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新的动漫生成项目
    
    Args:
        project: 项目创建请求
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        ProjectResponse: 创建的项目信息
    """
    pass
```

**请求模型**:
```python
class ProjectCreate(BaseModel):
    novel_text: str = Field(..., min_length=100, max_length=50000)
    options: Optional[ProjectOptions] = None
    
class ProjectOptions(BaseModel):
    style: str = Field(default="anime")
    quality: str = Field(default="standard")
    max_scenes: int = Field(default=30, ge=1, le=100)
```

**响应模型**:
```python
class ProjectResponse(BaseModel):
    id: UUID
    status: ProjectStatus
    progress: int = 0
    created_at: datetime
    estimated_time: Optional[int] = None
```

#### 获取项目详情
```python
@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取项目详细信息
    
    Args:
        project_id: 项目ID
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        ProjectDetail: 项目详细信息
    """
    pass
```

**响应模型**:
```python
class ProjectDetail(BaseModel):
    id: UUID
    status: ProjectStatus
    progress: int
    current_stage: Optional[str]
    novel_text: str
    characters: List[CharacterInfo]
    scenes: List[SceneInfo]
    video_url: Optional[str]
    created_at: datetime
    updated_at: datetime
```

#### 开始生成视频
```python
@router.post("/projects/{project_id}/generate", status_code=202)
async def generate_video(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    开始异步生成视频
    
    Args:
        project_id: 项目ID
        background_tasks: 后台任务
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        TaskResponse: 任务信息
    """
    # 添加后台任务
    background_tasks.add_task(
        generate_anime_video_task,
        project_id=project_id
    )
    
    return TaskResponse(
        task_id=str(project_id),
        status="processing",
        message="视频生成任务已启动"
    )
```

#### 获取项目列表
```python
@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[ProjectStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的项目列表
    
    Args:
        skip: 跳过数量
        limit: 返回数量
        status: 状态过滤
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        List[ProjectResponse]: 项目列表
    """
    pass
```

### 3.2 视频管理接口

#### 获取视频信息
```python
@router.get("/videos/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取视频信息
    
    Args:
        video_id: 视频ID
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        VideoResponse: 视频信息
    """
    pass
```

**响应模型**:
```python
class VideoResponse(BaseModel):
    id: UUID
    project_id: UUID
    video_url: str
    thumbnail_url: str
    duration: float
    file_size: int
    created_at: datetime
```

### 3.3 WebSocket接口

#### 实时进度推送
```python
@router.websocket("/ws/projects/{project_id}")
async def websocket_progress(
    websocket: WebSocket,
    project_id: UUID,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    WebSocket连接，实时推送项目进度
    
    Args:
        websocket: WebSocket连接
        project_id: 项目ID
        token: 认证token
        db: 数据库会话
    """
    # 验证token
    user = await verify_token(token)
    if not user:
        await websocket.close(code=1008)
        return
    
    # 接受连接
    await websocket.accept()
    
    try:
        # 订阅Redis频道
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"project:{project_id}:progress")
        
        # 持续推送进度
        async for message in pubsub.listen():
            if message["type"] == "message":
                progress_data = json.loads(message["data"])
                await websocket.send_json(progress_data)
                
                # 如果任务完成或失败，关闭连接
                if progress_data.get("status") in ["completed", "failed"]:
                    break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for project {project_id}")
    finally:
        await pubsub.unsubscribe(f"project:{project_id}:progress")
        await websocket.close()
```

**消息格式**:
```python
class ProgressMessage(BaseModel):
    type: str = "progress"  # progress, completed, error
    stage: str
    progress: int  # 0-100
    message: str
    current_scene: Optional[int] = None
    total_scenes: Optional[int] = None
    
class CompletedMessage(BaseModel):
    type: str = "completed"
    video_url: str
    thumbnail_url: str
    duration: float
    
class ErrorMessage(BaseModel):
    type: str = "error"
    error: str
    details: Optional[str] = None
```

## 4. 数据模型 (Schemas)

### 4.1 项目模型

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

class ProjectStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ProjectCreate(BaseModel):
    novel_text: str = Field(..., min_length=100, max_length=50000)
    options: Optional[ProjectOptions] = None
    
    @validator("novel_text")
    def validate_novel_text(cls, v):
        if not v.strip():
            raise ValueError("小说内容不能为空")
        return v.strip()

class ProjectOptions(BaseModel):
    style: str = Field(default="anime")
    quality: str = Field(default="standard")  # standard, high
    max_scenes: int = Field(default=30, ge=1, le=100)
    enable_bgm: bool = Field(default=False)

class ProjectResponse(BaseModel):
    id: UUID
    status: ProjectStatus
    progress: int = 0
    created_at: datetime
    estimated_time: Optional[int] = None
    
    class Config:
        orm_mode = True

class CharacterInfo(BaseModel):
    id: UUID
    name: str
    description: str
    reference_image_url: Optional[str]

class SceneInfo(BaseModel):
    id: UUID
    scene_number: int
    description: str
    image_url: Optional[str]
    audio_url: Optional[str]
    duration: float

class ProjectDetail(ProjectResponse):
    novel_text: str
    characters: List[CharacterInfo] = []
    scenes: List[SceneInfo] = []
    video_url: Optional[str] = None
    updated_at: datetime
```

### 4.2 通用模型

```python
class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    estimated_time: Optional[int] = None

class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
    error_code: Optional[str] = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    skip: int
    limit: int
```

## 5. 依赖注入

```python
# dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from typing import Optional

security = HTTPBearer()

async def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_redis():
    """获取Redis连接"""
    return await aioredis.from_url("redis://localhost")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前认证用户"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

async def verify_project_access(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Project:
    """验证项目访问权限"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return project
```

## 6. 中间件

```python
# middleware.py

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 记录请求
        logger.info(f"Request: {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        # 记录响应
        process_time = time.time() - start_time
        logger.info(
            f"Response: {response.status_code} "
            f"Time: {process_time:.3f}s"
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        return response

class CORSMiddleware:
    """CORS中间件"""
    # FastAPI自带，配置即可
    pass

class RateLimitMiddleware:
    """限流中间件"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        # 使用Redis实现分布式限流
```

## 7. 错误处理

```python
# app.py

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数验证错误处理"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": exc.errors()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "details": str(exc) if DEBUG else None
        }
    )
```

## 8. 限流策略

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 使用示例
@router.post("/projects")
@limiter.limit("10/minute")  # 每分钟最多10个请求
async def create_project(...):
    pass
```

## 9. 认证授权

```python
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)
```

## 10. API文档

FastAPI自动生成OpenAPI文档:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 11. 测试

```python
# tests/test_api.py

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_create_project():
    response = client.post(
        "/api/v1/projects",
        json={
            "novel_text": "这是一个测试小说..." * 100,
            "options": {
                "style": "anime",
                "quality": "standard"
            }
        },
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 201
    assert "id" in response.json()

def test_get_project():
    project_id = "test-uuid"
    response = client.get(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 200
```

## 12. 性能优化

### 12.1 异步处理
- 所有IO操作使用async/await
- 使用异步数据库驱动
- 使用异步Redis客户端

### 12.2 连接池
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True
)
```

### 12.3 响应压缩
```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

## 13. 监控指标

- API请求总数
- API响应时间
- 错误率
- 并发连接数
- WebSocket连接数

## 14. 接口安全

- HTTPS通信
- JWT Token认证
- API请求签名
- SQL注入防护
- XSS防护
- CSRF防护
- 限流保护
