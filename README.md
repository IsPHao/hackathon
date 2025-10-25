# 动漫生成平台

一个基于AI的动漫视频生成平台，可以从文本小说自动生成动漫视频。

## 项目概述

本项目是一个端到端的动漫视频生成系统，能够将小说文本转换为完整的动漫视频。系统使用多个AI Agent协同工作，包括：

1. 小说解析Agent - 提取角色和场景信息
2. 分镜设计Agent - 创建详细的分镜脚本
3. 角色一致性Agent - 确保角色外观在所有场景中保持一致
4. 图像生成Agent - 生成场景图片（支持文生图和图生图）
5. 语音合成Agent - 生成角色对话音频
6. 视频合成Agent - 将图片和音频合成最终视频

## 技术架构

- 后端：Python + FastAPI
- 前端：React + TypeScript
- AI模型：集成多个大模型服务
- 存储：本地存储 + 对象存储

## 图像生成Agent重构说明

图像生成Agent已经重构，现在支持使用七牛云AI API进行图像生成，包括：

1. 文生图（Text-to-Image）功能
2. 图生图（Image-to-Image）功能

### 支持的模型

- Qwen-Image系列模型
- WanX系列模型

### 配置说明

需要在配置中提供七牛云的API Key：

```python
config = ImageGeneratorConfig(
    qiniu_api_key="your_api_key",
    model="qwen-image-plus",  # 模型名称
    size="1024x1024",         # 图像尺寸
    generation_mode="text2image"  # 生成模式：text2image 或 image2image
)
```

### 使用方法

```python
agent = ImageGeneratorAgent(task_id="task-123", config=config)

# 文生图
image_path = await agent.generate(scene_data, character_templates)

# 图生图
reference_image_data = open("reference.png", "rb").read()
image_path = await agent.generate(scene_data, character_templates, reference_image=reference_image_data)
```

### API响应处理

图像生成Agent现在能够正确处理七牛云AI API的响应格式：

```json
{
  "created": 1234567890,
  "data": [
    {
      "b64_json": "iVBORw0KGgoAAAANSUhEUgA..."
    }
  ],
  "size": "1024x1024",
  "quality": "hd",
  "output_format": "png",
  "usage": {
    "total_tokens": 5234,
    "input_tokens": 234,
    "output_tokens": 5000,
    "input_tokens_details": {
      "text_tokens": 234,
      "image_tokens": 0
    }
  }
}
```

Agent会自动解析[data](file:///home/ubuntu/workspace/demo/hackathon/backend/src/agents/base/storage.py#L28-L28)数组中的第一个图像的[b64_json](file:///home/ubuntu/workspace/demo/hackathon/backend/src/agents/image_generator/agent.py#L230-L230)字段，并将其解码为图像数据。

## 快速开始

### 后端启动

```bash
cd backend
pip install -r requirements.txt
python -m src.main
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

## 测试

运行测试：

```bash
cd backend
pytest tests/ -v
```