# Storyboard Agent 设计文档

## 1. Agent概述

### 1.1 职责
分镜Agent负责将解析后的小说数据转换为分镜脚本，设计每个镜头的构图、时长和转场。

### 1.2 核心功能
- 场景分镜设计
- 镜头规划（景别、角度）
- 时长分配
- 图像生成prompt生成
- 转场设计

## 2. 模型选择

### Phase 1: GPT-4o-mini
- 成本: $0.10/小说
- 速度: <5s
- 足够的创意能力

### Phase 2: Claude 3.5 Sonnet  
- 更强创意能力
- 更好的分镜设计
- 成本: $0.30/小说

## 3. 输入输出

**输入**: Novel Parser的输出

**输出**:
```json
{
  "scenes": [
    {
      "scene_id": 1,
      "duration": 5.0,
      "shot_type": "medium_shot",
      "camera_angle": "eye_level",
      "camera_movement": "static",
      "transition": "fade",
      "image_prompt": "anime style, classroom, morning sunlight...",
      "composition": "rule of thirds, character on right",
      "lighting": "soft morning light from window",
      "mood": "peaceful, studious"
    }
  ]
}
```

## 4. Prompt设计

```python
STORYBOARD_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的动画分镜师,擅长将场景转换为详细的分镜脚本。"),
    ("human", """将以下场景转换为分镜脚本。

场景信息:
{scene_info}

角色信息:
{characters_info}

请为每个场景设计:
1. 镜头类型 (shot_type):
   - close_up: 特写镜头
   - medium_shot: 中景镜头
   - full_shot: 全景镜头
   - wide_shot: 远景镜头
   - extreme_close_up: 大特写

2. 镜头角度 (camera_angle):
   - eye_level: 平视
   - high_angle: 俯视
   - low_angle: 仰视
   - overhead: 顶视
   - dutch_angle: 斜角

3. 镜头运动 (camera_movement):
   - static: 静止
   - pan: 摇移
   - tilt: 俯仰
   - dolly: 推拉
   - tracking: 跟随

4. 时长 (duration):
   - 基于对话长度和动作数量计算
   - 对话: 约3字/秒
   - 动作: 每个动作约1.5秒
   - 最小3秒,最大10秒

5. 图像生成prompt (image_prompt):
   - 详细的视觉描述,包含环境、角色、光线、氛围
   - 使用anime style风格
   - 包含具体的构图要素

6. 构图 (composition):
   - rule_of_thirds: 三分法
   - centered: 居中构图
   - symmetrical: 对称构图
   - leading_lines: 引导线构图

7. 光线 (lighting):
   - natural: 自然光
   - soft: 柔光
   - dramatic: 戏剧性光线
   - backlight: 背光
   - side_light: 侧光

8. 转场效果 (transition):
   - cut: 切换
   - fade: 淡入淡出
   - dissolve: 溶解
   - wipe: 划像
   - none: 无转场

9. 情绪氛围 (mood):
   - 描述场景的情绪和氛围

请以JSON格式输出,严格遵循以下schema:
{
    "scenes": [
        {
            "scene_id": 场景编号(数字),
            "duration": 时长(浮点数),
            "shot_type": "镜头类型",
            "camera_angle": "镜头角度",
            "camera_movement": "镜头运动",
            "transition": "转场效果",
            "image_prompt": "详细的图像生成描述",
            "composition": "构图原则",
            "lighting": "光线设计",
            "mood": "情绪氛围"
        }
    ]
}""")
])
```

## 5. 核心实现

```python
class StoryboardAgent(BaseAgent[StoryboardConfig]):
    async def execute(self, novel_data: Dict, **kwargs) -> Dict:
        """执行分镜设计(统一接口)"""
        # 实现详情请查看 agent.py 文件
    
    async def create(self, novel_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建分镜脚本"""
        # 验证输入
        # 格式化场景和角色信息
        # 调用LLM生成分镜
        # 增强场景信息（计算时长、完善图像prompt）
        pass
```

## 6. 时长计算

```python
def _calculate_duration(self, dialogue: List[Dict[str, str]], actions: List[str]) -> float:
    """
    计算场景时长
    
    规则：
    - 对话：平均3字/秒（可通过配置调整）
    - 动作：每个动作1.5秒（可通过配置调整）
    - 最小时长：3秒（可通过配置调整）
    - 最大时长：10秒（可通过配置调整）
    """
    # 具体实现在 agent.py 中
    pass
```

## 7. 图像Prompt生成

```python
def _enhance_image_prompt(self, base_prompt: str, scene: Dict[str, Any]) -> str:
    """增强图像生成prompt"""
    # 具体实现在 agent.py 中
    pass
```

## 8. 性能指标

- 处理时长: <5秒/30场景
- 时长准确性: ±10%
- Prompt质量: 人工评估>85%