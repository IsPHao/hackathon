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
STORYBOARD_PROMPT = """
作为专业动画分镜师，将以下场景转换为分镜脚本。

场景信息：
{scene_info}

角色信息：
{characters_info}

请为每个场景设计：
1. 镜头类型（特写/近景/中景/远景/全景）
2. 镜头角度（仰视/平视/俯视）
3. 镜头运动（静止/推拉/摇移/跟随）
4. 时长（基于对话和动作）
5. 图像生成prompt（详细的视觉描述）
6. 构图原则
7. 光线设计
8. 转场效果

输出JSON格式。
"""
```

## 5. 核心实现

```python
class StoryboardAgent:
    async def create(self, novel_data: Dict) -> Dict:
        """创建分镜脚本"""
        scenes = []
        
        for scene in novel_data["scenes"]:
            storyboard_scene = await self._design_scene(
                scene,
                novel_data["characters"]
            )
            scenes.append(storyboard_scene)
        
        return {"scenes": scenes}
    
    async def _design_scene(self, scene: Dict, characters: List) -> Dict:
        """设计单个场景的分镜"""
        # 调用LLM生成分镜
        # 计算时长
        # 生成图像prompt
        pass
```

## 6. 时长计算

```python
def calculate_duration(dialogue: str, actions: List[str]) -> float:
    """
    计算场景时长
    
    规则：
    - 对话：平均3字/秒
    - 动作：每个动作1-2秒
    - 最小时长：3秒
    - 最大时长：10秒
    """
    dialogue_duration = len(dialogue) / 3 if dialogue else 0
    action_duration = len(actions) * 1.5
    
    total = max(3, min(10, dialogue_duration + action_duration))
    return round(total, 1)
```

## 7. 图像Prompt生成

```python
def generate_image_prompt(scene: Dict, characters: Dict) -> str:
    """生成图像生成prompt"""
    prompt_parts = [
        "anime style",
        f"location: {scene['location']}",
        f"time: {scene['time']}",
        f"atmosphere: {scene['atmosphere']}",
        f"lighting: {scene.get('lighting', 'natural')}",
        f"characters: {', '.join(scene['characters'])}",
        scene['description'],
        "high quality, detailed, cinematic"
    ]
    
    return ", ".join(prompt_parts)
```

## 8. 性能指标

- 处理时长: <5秒/30场景
- 时长准确性: ±10%
- Prompt质量: 人工评估>85%
