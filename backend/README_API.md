# 小说上传与处理进度 API 文档

## 概述

本 API 提供小说文本上传和处理进度查询功能，支持异步处理小说文本并实时查询处理进度。

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API 版本**: v1
- **内容类型**: `application/json`

## 接口列表

### 1. 健康检查

检查 API 服务健康状态。

**请求**
```http
GET /health
```

**响应示例**
```json
{
  "status": "healthy",
  "service": "anime-generation-api"
}
```

---

### 2. 上传小说文本

上传小说文本并开始异步处理，返回任务 ID 用于后续查询进度。

**请求**
```http
POST /api/v1/novels/upload
Content-Type: application/json
```

**请求体**
```json
{
  "novel_text": "小说内容文本...",
  "mode": "enhanced",
  "options": {
    "max_characters": 10,
    "max_scenes": 30
  }
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| novel_text | string | 是 | 小说文本内容，长度 100-100000 字符 |
| mode | string | 否 | 解析模式，可选值: `simple`, `enhanced`，默认 `enhanced` |
| options | object | 否 | 额外配置选项 |
| options.max_characters | int | 否 | 最大角色数量 |
| options.max_scenes | int | 否 | 最大场景数量 |

**响应示例 (202 Accepted)**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "message": "小说上传成功,正在处理中...",
  "created_at": "2024-10-24T12:00:00.000Z"
}
```

**错误响应**

- `422 Unprocessable Entity`: 参数验证失败
- `500 Internal Server Error`: 服务器内部错误

---

### 3. 查询处理进度

根据任务 ID 查询小说处理进度。

**请求**
```http
GET /api/v1/novels/{task_id}/progress
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | UUID | 任务 ID（从上传接口返回） |

**响应示例 - 处理中 (200 OK)**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "stage": "novel_parsing",
  "progress": 45,
  "message": "正在解析小说文本...",
  "result": null,
  "error": null
}
```

**响应示例 - 已完成 (200 OK)**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "stage": "completed",
  "progress": 100,
  "message": "小说解析完成",
  "result": {
    "characters": [
      {
        "name": "张三",
        "description": "主角，勇敢的冒险者",
        "appearance": {
          "age": "25岁",
          "gender": "男",
          "features": "黑发、蓝眼"
        }
      }
    ],
    "scenes": [
      {
        "scene_id": 1,
        "description": "冒险开始的小镇",
        "characters": ["张三"],
        "dialogue": "这是对白内容"
      }
    ],
    "plot_points": []
  },
  "error": null
}
```

**响应示例 - 失败 (200 OK)**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "failed",
  "stage": "novel_parsing",
  "progress": 30,
  "message": "处理失败",
  "result": null,
  "error": "API调用失败: 超时"
}
```

**状态字段说明**

| 状态 | 说明 |
|------|------|
| processing | 正在处理中 |
| completed | 处理完成 |
| failed | 处理失败 |

**错误响应**

- `404 Not Found`: 任务不存在
- `500 Internal Server Error`: 服务器内部错误

---

## 使用示例

### Python

```python
import requests
import time

# 1. 上传小说
upload_response = requests.post(
    "http://localhost:8000/api/v1/novels/upload",
    json={
        "novel_text": "这是一个关于勇者冒险的故事..." * 20,
        "mode": "enhanced"
    }
)

task_id = upload_response.json()["task_id"]
print(f"任务创建成功，ID: {task_id}")

# 2. 轮询查询进度
while True:
    progress_response = requests.get(
        f"http://localhost:8000/api/v1/novels/{task_id}/progress"
    )
    
    data = progress_response.json()
    print(f"进度: {data['progress']}% - {data['message']}")
    
    if data["status"] in ["completed", "failed"]:
        break
    
    time.sleep(2)

# 3. 获取结果
if data["status"] == "completed":
    print("处理完成!")
    print(f"角色数量: {len(data['result']['characters'])}")
    print(f"场景数量: {len(data['result']['scenes'])}")
else:
    print(f"处理失败: {data['error']}")
```

### JavaScript

```javascript
// 1. 上传小说
const uploadResponse = await fetch('http://localhost:8000/api/v1/novels/upload', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    novel_text: '这是一个关于勇者冒险的故事...'.repeat(20),
    mode: 'enhanced'
  })
});

const { task_id } = await uploadResponse.json();
console.log(`任务创建成功，ID: ${task_id}`);

// 2. 轮询查询进度
const pollProgress = async () => {
  const response = await fetch(
    `http://localhost:8000/api/v1/novels/${task_id}/progress`
  );
  const data = await response.json();
  
  console.log(`进度: ${data.progress}% - ${data.message}`);
  
  if (data.status === 'completed') {
    console.log('处理完成!');
    console.log(`角色数量: ${data.result.characters.length}`);
    console.log(`场景数量: ${data.result.scenes.length}`);
    return;
  } else if (data.status === 'failed') {
    console.log(`处理失败: ${data.error}`);
    return;
  }
  
  setTimeout(pollProgress, 2000);
};

pollProgress();
```

### cURL

```bash
# 1. 上传小说
curl -X POST http://localhost:8000/api/v1/novels/upload \
  -H "Content-Type: application/json" \
  -d '{
    "novel_text": "这是一个关于勇者冒险的故事...",
    "mode": "enhanced"
  }'

# 响应: {"task_id":"123e4567-e89b-12d3-a456-426614174000",...}

# 2. 查询进度
curl http://localhost:8000/api/v1/novels/123e4567-e89b-12d3-a456-426614174000/progress
```

---

## 启动服务

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
pip install fastapi uvicorn
```

### 设置环境变量

```bash
export OPENAI_API_KEY=your_openai_api_key
```

### 启动服务

```bash
# 方式 1: 直接运行
python -m src.api.app

# 方式 2: 使用 uvicorn
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

### 访问文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 注意事项

1. **文本长度限制**: 小说文本需要在 100-100000 字符之间
2. **异步处理**: 上传接口立即返回，实际处理在后台进行
3. **进度查询**: 建议每 2-5 秒轮询一次进度接口
4. **任务保留**: 任务结果保存在内存中，服务重启后会丢失
5. **并发限制**: 当前版本使用内存存储，建议生产环境配置 Redis

---

## 开发计划

未来版本将支持:

- [ ] WebSocket 实时推送进度
- [ ] Redis 持久化任务状态
- [ ] 数据库存储处理结果
- [ ] 任务取消功能
- [ ] 批量上传接口
