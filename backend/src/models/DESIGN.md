# Models 模块设计文档

## 1. 模块概述

Models模块定义所有数据模型，使用SQLAlchemy ORM。

## 2. 数据模型

### 2.1 Project
```python
from sqlalchemy import Column, String, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    novel_text = Column(Text, nullable=False)
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    characters = relationship("Character", back_populates="project")
    scenes = relationship("Scene", back_populates="project")
    videos = relationship("Video", back_populates="project")
```

### 2.2 Character
```python
class Character(Base):
    __tablename__ = "characters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    reference_image_url = Column(Text)
    features = Column(JSONB)
    created_at = Column(DateTime, default=func.now())
    
    project = relationship("Project", back_populates="characters")
```

### 2.3 Scene
```python
class Scene(Base):
    __tablename__ = "scenes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    scene_number = Column(Integer, nullable=False)
    description = Column(Text)
    image_url = Column(Text)
    audio_url = Column(Text)
    duration = Column(Float)
    metadata = Column(JSONB)
    created_at = Column(DateTime, default=func.now())
    
    project = relationship("Project", back_populates="scenes")
```

### 2.4 Video
```python
class Video(Base):
    __tablename__ = "videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    video_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text)
    duration = Column(Float)
    file_size = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())
    
    project = relationship("Project", back_populates="videos")
```

## 3. 数据库迁移

使用Alembic进行数据库迁移：

```bash
# 创建迁移
alembic revision --autogenerate -m "message"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```
