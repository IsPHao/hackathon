"""
缓存系统模块

提供内存缓存和可选的Redis缓存支持，用于提高性能和减少API调用成本。
"""
from typing import Any, Dict, Optional, Protocol
from abc import ABC, abstractmethod
import json
import hashlib
import logging
from datetime import datetime, timedelta
from collections import OrderedDict
import asyncio

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """
    缓存后端接口
    
    定义缓存后端必须实现的方法，支持内存和Redis两种实现。
    """
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            Optional[Any]: 缓存值，不存在时返回None
        """
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None表示永不过期
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        删除缓存
        
        Args:
            key: 缓存键
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否存在
        """
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """清空所有缓存"""
        pass


class MemoryCacheBackend(CacheBackend):
    """
    内存缓存后端
    
    使用OrderedDict实现LRU缓存策略，支持TTL过期。
    线程安全，适合单进程应用。
    
    Attributes:
        max_size: 最大缓存条目数
        _cache: 缓存数据存储
        _expiry: 过期时间存储
        _lock: 异步锁，保证线程安全
    """
    
    def __init__(self, max_size: int = 1000):
        """
        初始化内存缓存
        
        Args:
            max_size: 最大缓存条目数，超过后按LRU策略淘汰
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._expiry: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        自动检查过期时间，过期的缓存会被删除。
        访问的键会被移到最后（LRU策略）。
        
        Args:
            key: 缓存键
        
        Returns:
            Optional[Any]: 缓存值，不存在或已过期时返回None
        """
        async with self._lock:
            if key not in self._cache:
                return None
            
            if key in self._expiry and datetime.now() > self._expiry[key]:
                del self._cache[key]
                del self._expiry[key]
                logger.debug(f"Cache key '{key}' expired")
                return None
            
            self._cache.move_to_end(key)
            logger.debug(f"Cache hit for key '{key}'")
            return self._cache[key]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        超过最大容量时，删除最旧的缓存（LRU策略）。
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None表示永不过期
        """
        async with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                    self._expiry.pop(oldest_key, None)
                    logger.debug(f"Evicted oldest cache key '{oldest_key}' (LRU)")
            
            self._cache[key] = value
            
            if ttl is not None:
                self._expiry[key] = datetime.now() + timedelta(seconds=ttl)
            else:
                self._expiry.pop(key, None)
            
            logger.debug(f"Cache set for key '{key}' with TTL={ttl}")
    
    async def delete(self, key: str) -> None:
        """
        删除缓存
        
        Args:
            key: 缓存键
        """
        async with self._lock:
            self._cache.pop(key, None)
            self._expiry.pop(key, None)
            logger.debug(f"Cache deleted for key '{key}'")
    
    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        会检查过期时间，已过期的视为不存在。
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否存在且未过期
        """
        async with self._lock:
            if key not in self._cache:
                return False
            
            if key in self._expiry and datetime.now() > self._expiry[key]:
                del self._cache[key]
                del self._expiry[key]
                return False
            
            return True
    
    async def clear(self) -> None:
        """清空所有缓存"""
        async with self._lock:
            self._cache.clear()
            self._expiry.clear()
            logger.info("Memory cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 包含size、max_size、expired_count等统计信息
        """
        expired_count = sum(
            1 for key, expiry in self._expiry.items()
            if datetime.now() > expiry
        )
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "expired_count": expired_count,
            "backend": "memory"
        }


class RedisCacheBackend(CacheBackend):
    """
    Redis缓存后端
    
    使用Redis作为分布式缓存，支持多进程/多服务器共享缓存。
    自动序列化/反序列化Python对象。
    
    Attributes:
        redis: Redis客户端实例
        prefix: 键前缀，用于命名空间隔离
    """
    
    def __init__(self, redis_client, prefix: str = "cache:"):
        """
        初始化Redis缓存
        
        Args:
            redis_client: Redis客户端实例（如aioredis.Redis）
            prefix: 键前缀，用于命名空间隔离
        """
        self.redis = redis_client
        self.prefix = prefix
    
    def _make_key(self, key: str) -> str:
        """
        生成带前缀的完整键名
        
        Args:
            key: 原始键
        
        Returns:
            str: 带前缀的键名
        """
        return f"{self.prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """
        从Redis获取缓存值
        
        自动反序列化JSON数据。
        
        Args:
            key: 缓存键
        
        Returns:
            Optional[Any]: 缓存值，不存在时返回None
        """
        try:
            full_key = self._make_key(key)
            data = await self.redis.get(full_key)
            
            if data is None:
                return None
            
            logger.debug(f"Redis cache hit for key '{key}'")
            return json.loads(data)
        
        except Exception as e:
            logger.error(f"Failed to get from Redis cache: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置Redis缓存值
        
        自动序列化为JSON格式。
        
        Args:
            key: 缓存键
            value: 缓存值（必须可JSON序列化）
            ttl: 过期时间（秒），None表示永不过期
        """
        try:
            full_key = self._make_key(key)
            data = json.dumps(value, ensure_ascii=False)
            
            if ttl is not None:
                await self.redis.setex(full_key, ttl, data)
            else:
                await self.redis.set(full_key, data)
            
            logger.debug(f"Redis cache set for key '{key}' with TTL={ttl}")
        
        except Exception as e:
            logger.error(f"Failed to set Redis cache: {e}")
    
    async def delete(self, key: str) -> None:
        """
        删除Redis缓存
        
        Args:
            key: 缓存键
        """
        try:
            full_key = self._make_key(key)
            await self.redis.delete(full_key)
            logger.debug(f"Redis cache deleted for key '{key}'")
        
        except Exception as e:
            logger.error(f"Failed to delete from Redis cache: {e}")
    
    async def exists(self, key: str) -> bool:
        """
        检查Redis缓存是否存在
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否存在
        """
        try:
            full_key = self._make_key(key)
            return await self.redis.exists(full_key) > 0
        
        except Exception as e:
            logger.error(f"Failed to check Redis cache existence: {e}")
            return False
    
    async def clear(self) -> None:
        """
        清空所有带前缀的Redis缓存
        
        使用SCAN命令避免阻塞Redis服务器。
        """
        try:
            pattern = f"{self.prefix}*"
            cursor = 0
            
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                
                if keys:
                    await self.redis.delete(*keys)
                
                if cursor == 0:
                    break
            
            logger.info(f"Redis cache cleared (prefix: {self.prefix})")
        
        except Exception as e:
            logger.error(f"Failed to clear Redis cache: {e}")


class CacheManager:
    """
    缓存管理器
    
    提供统一的缓存接口，自动处理键生成和序列化。
    支持自动降级：Redis不可用时降级到内存缓存。
    
    Attributes:
        backend: 缓存后端实例
        default_ttl: 默认过期时间（秒）
    """
    
    def __init__(
        self,
        backend: Optional[CacheBackend] = None,
        default_ttl: int = 3600
    ):
        """
        初始化缓存管理器
        
        Args:
            backend: 缓存后端，默认使用内存缓存
            default_ttl: 默认过期时间（秒）
        """
        self.backend = backend or MemoryCacheBackend()
        self.default_ttl = default_ttl
    
    @staticmethod
    def make_cache_key(*parts: str) -> str:
        """
        生成缓存键
        
        使用SHA256对多个部分生成唯一的缓存键。
        
        Args:
            *parts: 键的组成部分
        
        Returns:
            str: 生成的缓存键
        
        Example:
            >>> CacheManager.make_cache_key("novel", "parse", "text_hash")
            "novel:parse:abc123..."
        """
        key_base = ":".join(str(p) for p in parts)
        key_hash = hashlib.sha256(key_base.encode()).hexdigest()[:16]
        return f"{parts[0]}:{key_hash}"
    
    async def get_or_compute(
        self,
        key: str,
        compute_func,
        *args,
        ttl: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        获取缓存或计算新值
        
        如果缓存存在则返回，否则调用compute_func计算并缓存结果。
        
        Args:
            key: 缓存键
            compute_func: 计算函数（可以是同步或异步函数）
            *args: 传递给compute_func的位置参数
            ttl: 过期时间（秒），None使用默认值
            **kwargs: 传递给compute_func的关键字参数
        
        Returns:
            Any: 缓存值或计算结果
        
        Example:
            >>> result = await cache.get_or_compute(
            ...     "novel:parse:abc",
            ...     parse_novel,
            ...     novel_text,
            ...     ttl=1800
            ... )
        """
        cached = await self.backend.get(key)
        
        if cached is not None:
            logger.info(f"Cache hit for key '{key}'")
            return cached
        
        logger.info(f"Cache miss for key '{key}', computing...")
        
        if asyncio.iscoroutinefunction(compute_func):
            result = await compute_func(*args, **kwargs)
        else:
            result = compute_func(*args, **kwargs)
        
        ttl = ttl if ttl is not None else self.default_ttl
        await self.backend.set(key, result, ttl=ttl)
        
        return result
    
    async def invalidate(self, key: str) -> None:
        """
        使缓存失效
        
        Args:
            key: 缓存键
        """
        await self.backend.delete(key)
        logger.info(f"Invalidated cache for key '{key}'")
    
    async def clear_all(self) -> None:
        """清空所有缓存"""
        await self.backend.clear()
        logger.info("All cache cleared")
