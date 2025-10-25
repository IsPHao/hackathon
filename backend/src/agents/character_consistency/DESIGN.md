# Character Consistency Agent 设计文档

## 1. Agent概述

### 1.1 职责
角色一致性Agent负责管理角色的视觉一致性，确保同一角色在不同场景中保持相同的外貌。

### 1.2 核心功能
- 角色库管理
- 首次角色生成
- 特征模板创建
- 一致性验证

## 2. 一致性方案

### Phase 1: Prompt + Seed固定
- 方法：详细prompt + 固定seed
- 一致性：70-80%
- 实现简单，适合快速开发

### Phase 2: IPAdapter + ControlNet
- 方法：参考图 + IPAdapter-FaceID
- 一致性：90%+
- 需要配置Stable Diffusion环境

## 3. 角色库设计

```python
class CharacterTemplate:
    """角色特征模板"""
    
    def __init__(self, character_data: Dict[str, Any]):
        self.name = character_data.get("name", "")
        self.base_prompt = character_data.get("base_prompt", "")
        self.negative_prompt = character_data.get("negative_prompt", "low quality, blurry, distorted")
        self.features = character_data.get("features", {})
        self.reference_image_url = character_data.get("reference_image_url")
        self.seed = self._generate_seed(self.name)
    
    def _generate_seed(self, name: str) -> int:
        """从角色名称生成稳定的随机种子"""
        hash_val = int(hashlib.sha256(name.encode('utf-8')).hexdigest(), 16)
        return hash_val % (2**32)
    
    def create_scene_prompt(self, scene_context: str) -> str:
        """为特定场景创建图像生成提示词"""
        return SCENE_PROMPT_TEMPLATE.format(
            base_prompt=self.base_prompt,
            scene_context=scene_context
        )

class LocalFileStorage(StorageInterface):
    """本地文件存储实现"""
    
    def __init__(self, base_path: str = "data/characters"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def save_character(self, project_id: str, character_name: str, data: Dict[str, Any]) -> str:
        """保存角色数据到本地文件"""
        # 实现详情请查看 storage.py 文件
    
    async def load_character(self, project_id: str, character_name: str) -> Optional[Dict[str, Any]]:
        """从本地文件加载角色数据"""
        # 实现详情请查看 storage.py 文件
```

## 4. 特征模板

```python
CHARACTER_FEATURE_EXTRACTION_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "You are a professional character design expert. Extract detailed visual features for consistent image generation."),
    ("human", """Based on the following character information, extract detailed visual features for consistent image generation.

Character Name: {name}
Description: {description}
Appearance: {appearance}

Please provide a detailed prompt template for generating this character's reference image.
The reference image should:
1. Include ALL distinctive features of the character
2. Be a full body portrait on white background
3. Have no environmental elements
4. Focus on the character's appearance only

Return a JSON object with the following structure:
{
    "base_prompt": "detailed prompt for the character",
    "negative_prompt": "things to avoid in the image",
    "features": {
        "gender": "male/female",
        "age": "age description",
        "hair": "detailed hair description",
        "eyes": "detailed eye description",
        "clothing": "detailed clothing description",
        "distinctive_features": "unique characteristics"
    }
}""")
])
```

## 5. 核心实现

```python
class CharacterConsistencyAgent(BaseAgent[CharacterConsistencyConfig]):
    
    async def execute(self, characters: List[Dict[str, Any]], project_id: str, **kwargs) -> Dict[str, CharacterTemplate]:
        """执行角色一致性管理(统一接口)"""
        # 实现详情请查看 agent.py 文件
    
    async def manage(
        self,
        characters: List[Dict[str, Any]],
        project_id: str,
    ) -> Dict[str, CharacterTemplate]:
        """管理项目中的所有角色"""
        # 1. 验证输入
        # 2. 遍历角色列表
        # 3. 检查缓存和存储中是否已存在角色
        # 4. 如果不存在，提取特征并创建新模板
        # 5. 保存到存储
        # 6. 更新缓存
        pass
    
    async def _extract_character_features(
        self,
        character_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取角色特征"""
        # 使用LLM从角色描述中提取详细视觉特征
        pass
    
    def _build_base_prompt(self, features_data: Dict[str, Any]) -> str:
        """构建基础提示词"""
        # 根据提取的特征构建基础提示词
        pass
```

## 6. 存储接口

```python
class StorageInterface(ABC):
    """存储接口"""
    
    @abstractmethod
    async def save_character(self, project_id: str, character_name: str, data: Dict[str, Any]) -> str:
        pass
    
    @abstractmethod
    async def load_character(self, project_id: str, character_name: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def character_exists(self, project_id: str, character_name: str) -> bool:
        pass
    
    @abstractmethod
    async def save_reference_image(self, project_id: str, character_name: str, image_url: str) -> str:
        pass
```

## 7. 性能指标

- 角色创建时长: <10秒/角色
- 一致性评分: >75% (Phase 1), >90% (Phase 2)
- 缓存命中率: >80%