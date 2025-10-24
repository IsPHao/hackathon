# Novel Parser Agent 设计文档

## 1. Agent概述

### 1.1 职责
小说解析Agent负责将输入的小说文本解析成结构化数据，为后续的分镜和内容生成提供基础。

### 1.2 核心功能
- 文本分段：将小说分割成多个场景
- 角色提取：识别并提取所有主要角色及其特征
- 场景识别：识别场景的地点、时间、氛围
- 对白提取：提取角色对话和旁白
- 关键情节点识别：提取故事的关键转折点

### 1.3 输入输出

**输入**:
```python
{
    "novel_text": "小说全文...",
    "options": {
        "max_characters": 10,  # 最多提取角色数
        "max_scenes": 30       # 最多场景数
    }
}
```

**输出**:
```python
{
    "characters": [
        {
            "name": "小明",
            "description": "一个16岁的高中生，性格开朗，喜欢打篮球",
            "appearance": {
                "gender": "male",
                "age": 16,
                "hair": "短黑发",
                "eyes": "棕色眼睛",
                "clothing": "校服",
                "features": "阳光笑容"
            },
            "personality": "开朗、热情、勇敢"
        }
    ],
    "scenes": [
        {
            "scene_id": 1,
            "location": "学校教室",
            "time": "早晨",
            "characters": ["小明", "小红"],
            "description": "阳光透过窗户洒进教室，小明正在认真听课",
            "dialogue": [
                {"character": "老师", "text": "今天我们来学习..."},
                {"character": "小明", "text": "老师，我有个问题"}
            ],
            "actions": ["小明举手提问", "老师走到讲台"],
            "atmosphere": "安静、专注"
        }
    ],
    "plot_points": [
        {
            "scene_id": 5,
            "type": "conflict",
            "description": "小明和小红发生争执"
        }
    ]
}
```

## 2. 技术实现

### 2.1 模型选择

#### Phase 1 (3天MVP)
**模型**: OpenAI GPT-4o-mini
- **理由**: 
  - 性价比高 ($0.15/M tokens)
  - 响应快速 (< 5s)
  - 理解能力足够
  - API稳定可靠
- **成本估算**: 每篇小说约$0.15

#### Phase 2 (优化)
**模型**: OpenAI GPT-4o
- **理由**:
  - 更强的理解能力
  - 更准确的角色特征提取
  - 更好的情节分析
- **成本估算**: 每篇小说约$5

#### 开源替代方案
**模型**: Qwen2.5-72B-Instruct
- **理由**:
  - 完全免费
  - 中文理解能力强
  - 可本地部署
- **部署要求**: 
  - GPU: A100 40GB x 2
  - 内存: 160GB+

### 2.2 Prompt设计

#### 主Prompt模板

```python
NOVEL_PARSE_PROMPT = """
你是一个专业的小说分析专家，擅长将小说文本解析成结构化数据。

请分析以下小说文本，提取以下信息：

1. **角色信息**（最多{max_characters}个主要角色）
   - 姓名
   - 详细外貌描述（性别、年龄、发型、眼睛、服装、特征）
   - 性格特点
   - 在故事中的作用

2. **场景信息**（最多{max_scenes}个关键场景）
   - 场景编号
   - 地点
   - 时间（具体时间或时间段）
   - 出现的角色
   - 场景描述（环境、氛围、光线）
   - 对话内容（角色+对话）
   - 动作描述
   - 场景氛围

3. **情节点**
   - 关键转折点
   - 冲突点
   - 高潮点

小说文本：
\"\"\"
{novel_text}
\"\"\"

请以JSON格式输出，严格遵循以下schema：
{{
    "characters": [
        {{
            "name": "角色名",
            "description": "简短描述",
            "appearance": {{
                "gender": "male/female",
                "age": 年龄（数字）,
                "hair": "发型和颜色",
                "eyes": "眼睛颜色和特征",
                "clothing": "典型服装",
                "features": "独特特征"
            }},
            "personality": "性格特点"
        }}
    ],
    "scenes": [
        {{
            "scene_id": 场景编号（数字）,
            "location": "地点",
            "time": "时间",
            "characters": ["角色1", "角色2"],
            "description": "场景描述",
            "dialogue": [
                {{"character": "角色", "text": "对话内容"}}
            ],
            "actions": ["动作1", "动作2"],
            "atmosphere": "氛围"
        }}
    ],
    "plot_points": [
        {{
            "scene_id": 场景编号,
            "type": "conflict/climax/resolution",
            "description": "描述"
        }}
    ]
}}

注意事项：
1. 角色外貌描述要详细具体，便于后续图像生成
2. 场景描述要视觉化，包含环境、光线、氛围等细节
3. 对话要保留原文，不要总结
4. 确保JSON格式正确，可以被解析
"""
```

#### 角色外貌增强Prompt

```python
CHARACTER_APPEARANCE_ENHANCE_PROMPT = """
基于以下角色基础信息，生成详细的视觉化外貌描述，用于图像生成。

角色信息：
姓名：{name}
基础描述：{description}

请生成一个详细的外貌描述，包括：
1. 整体风格（anime style / realistic / etc）
2. 性别和年龄
3. 发型和发色（详细描述）
4. 眼睛（颜色、形状、神态）
5. 面部特征（脸型、皮肤、特殊标记）
6. 身材体型
7. 典型服装（详细描述）
8. 独特标识（配饰、纹身等）
9. 整体气质

输出格式（用于图像生成）：
{{
    "prompt": "anime style, detailed character description...",
    "negative_prompt": "low quality, blurry...",
    "style_tags": ["anime", "high quality", "detailed"]
}}
"""
```

### 2.3 核心代码实现

```python
from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
import json
import logging

logger = logging.getLogger(__name__)

class NovelParserAgent:
    """
    小说解析Agent
    
    职责：
    - 解析小说文本
    - 提取角色和场景信息
    - 生成结构化数据
    """
    
    def __init__(
        self,
        llm: ChatOpenAI,
        max_characters: int = 10,
        max_scenes: int = 30
    ):
        self.llm = llm
        self.max_characters = max_characters
        self.max_scenes = max_scenes
    
    async def parse(
        self,
        novel_text: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        解析小说文本
        
        Args:
            novel_text: 小说文本
            options: 可选配置
        
        Returns:
            Dict: 解析结果
        
        Raises:
            ValidationError: 文本验证失败
            APIError: API调用失败
        """
        # 验证输入
        self._validate_input(novel_text)
        
        # 构建prompt
        prompt = self._build_prompt(novel_text, options)
        
        # 调用LLM
        response = await self._call_llm(prompt)
        
        # 解析响应
        parsed_data = self._parse_response(response)
        
        # 增强角色外貌描述
        parsed_data["characters"] = await self._enhance_characters(
            parsed_data["characters"]
        )
        
        # 验证输出
        self._validate_output(parsed_data)
        
        return parsed_data
    
    def _validate_input(self, novel_text: str):
        """验证输入"""
        if not novel_text or len(novel_text.strip()) < 100:
            raise ValidationError("小说文本过短")
        
        if len(novel_text) > 50000:
            raise ValidationError("小说文本过长")
    
    def _build_prompt(
        self,
        novel_text: str,
        options: Optional[Dict[str, Any]]
    ) -> str:
        """构建prompt"""
        max_characters = options.get("max_characters", self.max_characters) if options else self.max_characters
        max_scenes = options.get("max_scenes", self.max_scenes) if options else self.max_scenes
        
        return NOVEL_PARSE_PROMPT.format(
            novel_text=novel_text,
            max_characters=max_characters,
            max_scenes=max_scenes
        )
    
    async def _call_llm(self, prompt: str) -> str:
        """
        调用LLM API
        
        Args:
            prompt: 输入prompt
        
        Returns:
            str: LLM响应
        
        Raises:
            APIError: API调用失败
        """
        try:
            response = await self.llm.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional novel analysis expert."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # 较低的temperature保证稳定性
                response_format={"type": "json_object"}
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise APIError(f"Failed to call LLM API: {e}") from e
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析LLM响应
        
        Args:
            response: LLM响应
        
        Returns:
            Dict: 解析后的数据
        
        Raises:
            ParseError: 解析失败
        """
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ParseError(f"Invalid JSON response: {e}") from e
    
    async def _enhance_characters(
        self,
        characters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        增强角色外貌描述
        
        Args:
            characters: 角色列表
        
        Returns:
            List[Dict]: 增强后的角色列表
        """
        enhanced_characters = []
        
        for char in characters:
            # 为每个角色生成详细的视觉描述
            visual_desc = await self._generate_visual_description(char)
            char["visual_description"] = visual_desc
            enhanced_characters.append(char)
        
        return enhanced_characters
    
    async def _generate_visual_description(
        self,
        character: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        生成角色的视觉化描述
        
        Args:
            character: 角色信息
        
        Returns:
            Dict: 包含prompt和negative_prompt的视觉描述
        """
        prompt = CHARACTER_APPEARANCE_ENHANCE_PROMPT.format(
            name=character["name"],
            description=character["description"]
        )
        
        response = await self._call_llm(prompt)
        visual_desc = json.loads(response)
        
        return visual_desc
    
    def _validate_output(self, data: Dict[str, Any]):
        """验证输出数据"""
        required_keys = ["characters", "scenes", "plot_points"]
        for key in required_keys:
            if key not in data:
                raise ValidationError(f"Missing required key: {key}")
        
        if not data["characters"]:
            raise ValidationError("No characters extracted")
        
        if not data["scenes"]:
            raise ValidationError("No scenes extracted")
```

## 3. 优化策略

### 3.1 缓存策略

```python
import hashlib
from typing import Optional

class CachedNovelParser(NovelParserAgent):
    """带缓存的小说解析器"""
    
    def __init__(self, redis_client, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis = redis_client
    
    async def parse(self, novel_text: str, options: Optional[Dict] = None) -> Dict:
        # 生成缓存key
        cache_key = self._generate_cache_key(novel_text, options)
        
        # 检查缓存
        cached = await self.redis.get(cache_key)
        if cached:
            logger.info("Cache hit for novel parsing")
            return json.loads(cached)
        
        # 执行解析
        result = await super().parse(novel_text, options)
        
        # 保存到缓存（7天）
        await self.redis.setex(
            cache_key,
            7 * 24 * 3600,
            json.dumps(result)
        )
        
        return result
    
    def _generate_cache_key(self, novel_text: str, options: Optional[Dict]) -> str:
        """生成缓存key"""
        text_hash = hashlib.md5(novel_text.encode()).hexdigest()
        options_hash = hashlib.md5(json.dumps(options or {}).encode()).hexdigest()
        return f"novel_parse:{text_hash}:{options_hash}"
```

### 3.2 分块处理

对于超长小说，采用分块处理：

```python
async def parse_long_novel(self, novel_text: str) -> Dict:
    """处理超长小说"""
    # 按章节分割
    chapters = self._split_into_chapters(novel_text)
    
    # 并行处理每个章节
    chapter_results = await asyncio.gather(*[
        self.parse(chapter) for chapter in chapters
    ])
    
    # 合并结果
    merged_result = self._merge_results(chapter_results)
    
    return merged_result
```

## 4. 错误处理

```python
class NovelParserError(Exception):
    """小说解析错误基类"""
    pass

class ValidationError(NovelParserError):
    """验证错误"""
    pass

class ParseError(NovelParserError):
    """解析错误"""
    pass

class APIError(NovelParserError):
    """API调用错误"""
    pass
```

## 5. 测试

```python
import pytest

@pytest.mark.asyncio
async def test_parse_novel():
    # 外部创建LLM实例
    llm = ChatOpenAI(api_key="test-key")
    agent = NovelParserAgent(llm=llm)
    
    result = await agent.parse(TEST_NOVEL)
    
    assert "characters" in result
    assert len(result["characters"]) > 0
    assert "scenes" in result
    assert len(result["scenes"]) > 0

@pytest.mark.asyncio
async def test_parse_short_novel_fails():
    llm = ChatOpenAI(api_key="test-key")
    agent = NovelParserAgent(llm=llm)
    
    with pytest.raises(ValidationError):
        await agent.parse("太短了")
```

## 6. 性能指标

- 处理时长: < 10秒 (5000字小说)
- 成功率: > 95%
- 准确率: 
  - 角色提取: > 90%
  - 场景识别: > 85%
  - 对话提取: > 95%

## 7. 监控

- API调用次数
- API调用耗时
- 失败率
- 缓存命中率
- Token使用量和成本