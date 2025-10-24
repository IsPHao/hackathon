# 缓存系统使用说明

## 概述

缓存系统提供了灵活的缓存解决方案，默认使用内存缓存，支持可选的Redis扩展，用于提升性能和减少API调用成本。

## 主要特性

1. **内存缓存**（默认）
   - LRU（最近最少使用）淘汰策略
   - 支持TTL过期
   - 线程安全
   - 无需外部依赖

2. **Redis缓存**（可选）
   - 分布式缓存支持
   - 跨进程/服务器共享
   - 持久化支持
   - 高性能

3. **自动降级**
   - Redis不可用时自动降级到内存缓存
   - 透明的错误处理

## 基本使用

### 1. 使用内存缓存（默认）

```python
from core import CacheManager, MemoryCacheBackend

# 创建缓存管理器（使用内存缓存）
cache = CacheManager(
    backend=MemoryCacheBackend(max_size=1000),
    default_ttl=3600  # 默认1小时过期
)

# 获取或计算缓存
async def expensive_operation(text):
    # 模拟耗时操作
    await asyncio.sleep(2)
    return {"result": "processed"}

result = await cache.get_or_compute(
    "operation:abc123",
    expensive_operation,
    "some text",
    ttl=1800  # 30分钟过期
)
```

### 2. 使用Redis缓存

```python
from core import CacheManager, RedisCacheBackend
import aioredis

# 创建Redis客户端
redis_client = await aioredis.create_redis_pool("redis://localhost:6379")

# 创建缓存管理器（使用Redis）
cache = CacheManager(
    backend=RedisCacheBackend(
        redis_client,
        prefix="anime:"  # 键前缀，用于命名空间隔离
    ),
    default_ttl=3600
)

# 使用方式与内存缓存相同
result = await cache.get_or_compute(
    "operation:abc123",
    expensive_operation,
    "some text"
)
```

### 3. Agent中集成缓存

```python
from core import CacheManager, MemoryCacheBackend
import hashlib

class NovelParserAgent:
    def __init__(self, llm, config=None):
        self.llm = llm
        self.config = config or NovelParserConfig()
        
        # 初始化缓存
        self.cache = CacheManager(
            backend=MemoryCacheBackend(max_size=100),
            default_ttl=86400  # 24小时
        )
    
    async def parse(self, novel_text: str, mode: str = "enhanced") -> Dict[str, Any]:
        # 生成缓存键
        cache_key = CacheManager.make_cache_key(
            "novel",
            "parse",
            hashlib.sha256(novel_text.encode()).hexdigest()[:16],
            mode
        )
        
        # 使用缓存
        result = await self.cache.get_or_compute(
            cache_key,
            self._do_parse,
            novel_text,
            mode,
            ttl=86400  # 相同文本24小时内不重新解析
        )
        
        return result
    
    async def _do_parse(self, novel_text: str, mode: str) -> Dict[str, Any]:
        # 实际的解析逻辑
        if mode == "enhanced":
            return await self._parse_enhanced(novel_text)
        else:
            return await self._parse_simple(novel_text)
```

## 高级用法

### 1. 生成缓存键

```python
from core import CacheManager

# 方法1：使用静态方法生成
key = CacheManager.make_cache_key("novel", "parse", "text_hash")
# 输出: "novel:a1b2c3d4e5f6..."

# 方法2：手动拼接
import hashlib
text_hash = hashlib.sha256(novel_text.encode()).hexdigest()[:16]
key = f"novel:parse:{text_hash}"
```

### 2. 手动管理缓存

```python
# 直接使用后端接口
backend = MemoryCacheBackend(max_size=1000)

# 设置缓存
await backend.set("key1", {"data": "value"}, ttl=3600)

# 获取缓存
value = await backend.get("key1")

# 检查存在
exists = await backend.exists("key1")

# 删除缓存
await backend.delete("key1")

# 清空所有缓存
await backend.clear()
```

### 3. 查看缓存统计

```python
# 仅内存缓存支持
if isinstance(cache.backend, MemoryCacheBackend):
    stats = cache.backend.get_stats()
    print(f"缓存大小: {stats['size']}/{stats['max_size']}")
    print(f"过期项: {stats['expired_count']}")
```

### 4. 缓存失效

```python
# 使缓存失效
await cache.invalidate("novel:parse:abc123")

# 清空所有缓存
await cache.clear_all()
```

## 在Pipeline中使用

```python
from core import CacheManager, MemoryCacheBackend

class AnimePipeline:
    def __init__(self, ..., cache_manager: Optional[CacheManager] = None):
        # ... 其他初始化
        
        # 使用共享的缓存管理器或创建新的
        self.cache = cache_manager or CacheManager(
            backend=MemoryCacheBackend(max_size=500),
            default_ttl=3600
        )
    
    async def execute(self, project_id: UUID, novel_text: str, ...):
        # 缓存整个pipeline结果（可选）
        cache_key = CacheManager.make_cache_key(
            "pipeline",
            str(project_id),
            hashlib.sha256(novel_text.encode()).hexdigest()[:16]
        )
        
        # 注意：pipeline一般不缓存，这里仅作示例
        # 实际应用中应该缓存中间结果（如解析、分镜等）
```

## Redis配置扩展

### 1. 基本配置

```python
import aioredis

# 创建Redis连接池
redis_client = await aioredis.create_redis_pool(
    "redis://localhost:6379",
    minsize=5,
    maxsize=10,
    encoding="utf-8"
)

# 使用Redis缓存
cache = CacheManager(
    backend=RedisCacheBackend(redis_client, prefix="anime:"),
    default_ttl=3600
)
```

### 2. 集群配置

```python
import aioredis

# Redis集群配置
redis_client = await aioredis.create_redis_pool(
    [
        "redis://node1:6379",
        "redis://node2:6379",
        "redis://node3:6379"
    ],
    encoding="utf-8"
)
```

### 3. 哨兵模式

```python
import aioredis

# Redis哨兵配置
redis_client = await aioredis.create_redis_pool(
    [("sentinel1", 26379), ("sentinel2", 26379)],
    sentinel=True,
    sentinel_master="mymaster"
)
```

## 最佳实践

### 1. TTL设置建议

```python
# 小说解析结果：24小时（内容不常变）
novel_cache_ttl = 86400

# 图片生成提示：1小时（可能需要调整）
image_prompt_ttl = 3600

# 临时中间结果：5分钟
temp_result_ttl = 300
```

### 2. 缓存键命名规范

```python
# 推荐格式：{模块}:{操作}:{唯一标识}
"novel:parse:{text_hash}"
"image:generate:{scene_hash}"
"character:template:{char_name_hash}"
```

### 3. 内存vs Redis选择

**使用内存缓存的场景：**
- 单进程应用
- 缓存数据量小（<1GB）
- 不需要持久化
- 开发/测试环境

**使用Redis缓存的场景：**
- 多进程/多服务器部署
- 缓存数据量大
- 需要持久化
- 需要跨服务共享缓存
- 生产环境

### 4. 错误处理

```python
try:
    result = await cache.get_or_compute(
        key,
        expensive_func,
        *args,
        **kwargs
    )
except Exception as e:
    # 缓存失败不应该影响业务逻辑
    logger.warning(f"Cache operation failed: {e}")
    # 直接执行计算
    result = await expensive_func(*args, **kwargs)
```

## 性能优化建议

1. **合理设置max_size**：内存缓存不宜过大，建议100-1000之间
2. **TTL不宜过长**：避免缓存过期数据，建议根据数据更新频率设置
3. **批量操作**：对于大量缓存操作，考虑批量处理
4. **监控缓存命中率**：定期检查缓存效果，调整策略

## 故障排查

### 问题1：缓存未生效

**检查项：**
1. 确认缓存键生成逻辑一致
2. 检查TTL是否过短
3. 验证缓存容量是否足够

### 问题2：内存占用过高

**解决方案：**
1. 减小max_size
2. 缩短TTL
3. 切换到Redis

### 问题3：Redis连接失败

**解决方案：**
1. 检查Redis服务状态
2. 验证连接配置
3. 系统会自动降级到内存缓存

## 迁移指南

### 从无缓存迁移

```python
# 之前
result = await self.llm.ainvoke(messages)

# 之后
cache_key = CacheManager.make_cache_key("llm", "invoke", hash(str(messages)))
result = await self.cache.get_or_compute(
    cache_key,
    self.llm.ainvoke,
    messages,
    ttl=3600
)
```

### 从内存缓存迁移到Redis

```python
# 只需更换backend，代码无需修改
# 之前
cache = CacheManager(backend=MemoryCacheBackend())

# 之后
cache = CacheManager(backend=RedisCacheBackend(redis_client))
```
