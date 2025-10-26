# Backend - 智能动漫生成系统

## 项目结构

```
backend/
├── src/
│   ├── agents/          # Agent模块
│   │   └── novel_parser/  # 小说解析Agent
│   ├── api/             # API接口
│   ├── core/            # 核心业务逻辑
│   ├── models/          # 数据模型
│   └── services/        # 外部服务集成
├── tests/               # 测试文件
└── requirements.txt     # 项目依赖
```

## Novel Parser Agent

小说解析Agent负责将输入的小说文本解析成结构化数据。

### 功能特性

- **双模式支持**:
  - `simple`: 单次遍历,快速解析
  - `enhanced`: 多次遍历,合并角色信息,更准确

- **可配置参数**:
  - 模型选择(默认: gpt-4o-mini)
  - 最大角色数
  - 最大场景数
  - 温度参数
  - 缓存开关

- **缓存支持**: 支持Redis缓存,减少重复API调用

### 使用示例

```python
from openai import AsyncOpenAI
from backend.src.agents.novel_parser import NovelParserAgent, NovelParserConfig

# 创建LLM客户端
llm_client = AsyncOpenAI(api_key="your-api-key")

# 配置Agent
config = NovelParserConfig(
    model="gpt-4o-mini",
    max_characters=10,
    max_scenes=30
)

# 创建Agent实例
agent = NovelParserAgent(llm_client=llm_client, config=config)

# 解析小说 - 简单模式
result = await agent.parse(novel_text, mode="simple")

# 解析小说 - 增强模式(推荐用于长篇小说)
result = await agent.parse(novel_text, mode="enhanced")

# 自定义选项
result = await agent.parse(
    novel_text, 
    mode="enhanced",
    options={"max_characters": 15, "max_scenes": 50}
)
```

### 输出格式

返回类型为 `NovelParseResult` (Pydantic模型)，包含以下字段：

```python
{
    "characters": [
        {
            "name": "角色名",
            "description": "角色描述",
            "appearance": {
                "gender": "male/female/unknown",
                "age": 16,
                "age_stage": "年龄段(童年/少年/青年/中年/老年)",
                "hair": "发型描述",
                "eyes": "眼睛描述",
                "clothing": "服装描述",
                "features": "特征描述",
                "body_type": "体型特征",
                "height": "身高描述",
                "skin": "肤色特征"
            },
            "personality": "性格描述",
            "role": "在故事中的作用",
            "age_variants": [  # 不同年龄段的外貌变化
                {
                    "age_stage": "童年",
                    "appearance": {...}
                }
            ]
        }
    ],
    "scenes": [
        {
            "scene_id": 1,
            "location": "地点",
            "time": "时间",
            "characters": ["角色1", "角色2"],
            "description": "场景环境描述",
            "narration": "旁白内容",
            "dialogue": [
                {"character": "角色", "text": "对话内容"}
            ],
            "actions": ["动作1", "动作2"],
            "atmosphere": "氛围",
            "lighting": "光线描述",
            "character_appearances": {  # 场景中角色外貌更新
                "角色名": {
                    "gender": "male/female",
                    "age": 16,
                    "age_stage": "少年",
                    ...
                }
            }
        }
    ],
    "plot_points": [
        {
            "scene_id": 1,
            "type": "conflict/climax/resolution/normal",
            "description": "情节点描述"
        }
    ]
}
```

**新增特性：**
- ✨ 使用 Pydantic 模型进行数据验证和类型检查
- ✨ 支持角色年龄段分组 (`age_variants`)，可记录同一角色不同年龄的外貌
- ✨ 场景中分离旁白 (`narration`) 和对话 (`dialogue`)
- ✨ 场景中记录角色外貌更新 (`character_appearances`)
- ✨ 所有字段都有默认值，LLM 输出异常时也不会报错

## 安装

```bash
pip install -r requirements.txt
```

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/agents/novel_parser/

# 显示测试覆盖率
pytest --cov=backend.src.agents.novel_parser tests/agents/novel_parser/
```

## 配置参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| model | str | gpt-4o-mini | LLM模型名称 |
| max_characters | int | 10 | 最大角色数 |
| max_scenes | int | 30 | 最大场景数 |
| temperature | float | 0.3 | LLM温度参数 |
| enable_caching | bool | True | 启用缓存 |
| cache_ttl | int | 604800 | 缓存过期时间(秒) |
| min_text_length | int | 100 | 最小文本长度 |
| max_text_length | int | 50000 | 最大文本长度 |

## 性能指标

- 处理时长: < 10秒 (5000字小说, simple模式)
- 成功率: > 95%
- 准确率:
  - 角色提取: > 90%
  - 场景识别: > 85%
  - 对话提取: > 95%
