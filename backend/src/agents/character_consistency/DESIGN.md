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
class CharacterDatabase:
    """角色数据库"""
    
    def __init__(self, vector_db, storage):
        self.vector_db = vector_db  # Chroma
        self.storage = storage      # 对象存储
        self.cache = {}
    
    async def get_or_create(
        self,
        project_id: UUID,
        character_name: str,
        description: Dict
    ) -> Character:
        """获取或创建角色"""
        # 1. 检查缓存
        cache_key = f"{project_id}:{character_name}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 2. 检查数据库
        character = await self._find_in_db(project_id, character_name)
        if character:
            self.cache[cache_key] = character
            return character
        
        # 3. 创建新角色
        character = await self._create_character(
            project_id,
            character_name,
            description
        )
        
        # 4. 保存
        await self._save_character(character)
        self.cache[cache_key] = character
        
        return character
```

## 4. 特征模板

```python
class CharacterTemplate:
    """角色特征模板"""
    
    def __init__(self, character: Dict):
        self.name = character["name"]
        self.base_prompt = self._create_base_prompt(character)
        self.reference_image = None
        self.seed = self._generate_seed(character["name"])
    
    def _create_base_prompt(self, character: Dict) -> str:
        """创建基础prompt模板"""
        appearance = character["appearance"]
        
        template = f"""
        anime style,
        {appearance['gender']},
        {appearance['age']} years old,
        {appearance['hair']},
        {appearance['eyes']},
        {appearance['clothing']},
        {appearance['features']},
        consistent character design,
        high quality
        """
        
        return template.strip()
    
    def _generate_seed(self, name: str) -> int:
        """生成稳定的seed"""
        import hashlib
        hash_val = int(hashlib.md5(name.encode()).hexdigest(), 16)
        return hash_val % (2**32)
    
    def create_scene_prompt(self, scene_desc: str) -> str:
        """为特定场景创建prompt"""
        return f"{self.base_prompt}, {scene_desc}"
```

## 5. 核心实现

```python
class CharacterConsistencyAgent:
    
    async def manage(
        self,
        characters: List[Dict],
        project_id: UUID
    ) -> Dict[str, CharacterTemplate]:
        """管理项目中的所有角色"""
        character_templates = {}
        
        for char in characters:
            # 获取或创建角色
            character = await self.character_db.get_or_create(
                project_id,
                char["name"],
                char
            )
            
            # 创建特征模板
            template = CharacterTemplate(character)
            
            # 生成参考图（首次）
            if not character.reference_image:
                ref_image = await self._generate_reference_image(template)
                await self._save_reference_image(character, ref_image)
            
            character_templates[char["name"]] = template
        
        return character_templates
    
    async def _generate_reference_image(
        self,
        template: CharacterTemplate
    ) -> str:
        """生成角色参考图"""
        # 调用图像生成API
        # 使用详细prompt + 固定seed
        pass
```

## 6. 向量检索

```python
async def find_similar_character(
    self,
    description: str
) -> Optional[Character]:
    """通过语义检索相似角色"""
    # 使用Chroma向量数据库
    results = await self.vector_db.query(
        query_texts=[description],
        n_results=1
    )
    
    if results and results[0]["distance"] < 0.3:
        return results[0]["metadata"]
    
    return None
```

## 7. 性能指标

- 角色创建时长: <10秒/角色
- 一致性评分: >75% (Phase 1), >90% (Phase 2)
- 缓存命中率: >80%
