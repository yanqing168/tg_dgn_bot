"""
后缀管理模块
实现 0.001-0.999 后缀池（999个可用）
"""
import asyncio
import time
from typing import Optional, Set
import redis.asyncio as redis
from datetime import datetime, timedelta

from ..config import settings
from src.common.settings_service import get_order_timeout_minutes


class SuffixManager:
    """后缀管理器"""
    
    def __init__(self):
        self.redis_client = None
        self._local_cache: Set[int] = set()
        self._cache_lock = asyncio.Lock()
        
    async def connect(self):
        """连接Redis"""
        if not self.redis_client:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )
    
    async def disconnect(self):
        """断开Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def allocate_suffix(self, order_id: Optional[str] = None) -> Optional[int]:
        """
        分配唯一后缀 (1-999)
        
        Args:
            order_id: 订单ID
            
        Returns:
            分配的后缀，如果分配失败返回None
        """
        await self.connect()
        
        # 尝试分配后缀，最多重试3次
        for attempt in range(3):
            suffix = await self._try_allocate_suffix(order_id)
            if suffix is not None:
                return suffix
            
            # 短暂等待后重试
            await asyncio.sleep(0.01 * (attempt + 1))
        
        return None
    
    async def _try_allocate_suffix(self, order_id: Optional[str]) -> Optional[int]:
        """尝试分配后缀"""
        # 获取当前已使用的后缀
        used_suffixes = await self._get_used_suffixes()
        
        # 从1-999中找到未使用的后缀
        for suffix in range(1, 1000):
            if suffix not in used_suffixes:
                # 尝试占用这个后缀
                if await self._reserve_suffix(suffix, order_id):
                    return suffix
        
        return None
    
    async def _get_used_suffixes(self) -> Set[int]:
        """获取当前已使用的后缀"""
        # 从Redis中获取所有活跃的后缀
        pattern = "suffix:*"
        keys = await self.redis_client.keys(pattern)
        
        used_suffixes = set()
        for key in keys:
            try:
                suffix = int(key.split(":")[1])
                used_suffixes.add(suffix)
            except (IndexError, ValueError):
                continue
        
        return used_suffixes
    
    async def _reserve_suffix(self, suffix: int, order_id: Optional[str]) -> bool:
        """
        原子性地预留后缀
        
        Args:
            suffix: 要预留的后缀
            order_id: 订单ID
            
        Returns:
            是否成功预留
        """
        key = f"suffix:{suffix}"
        timeout_minutes = get_order_timeout_minutes()
        
        # 使用SET NX EX命令实现原子性预留
        result = await self.redis_client.set(
            key, 
            order_id or "pending",
            nx=True,  # 只在key不存在时设置
            ex=timeout_minutes * 60  # 过期时间（秒）
        )
        
        return result is True
    
    async def release_suffix(self, suffix: int, order_id: str) -> bool:
        """
        释放后缀
        
        Args:
            suffix: 要释放的后缀
            order_id: 订单ID（用于验证）
            
        Returns:
            是否成功释放
        """
        await self.connect()
        
        key = f"suffix:{suffix}"
        
        # 使用Lua脚本确保原子性：只有当值匹配时才删除
        lua_script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        else
            return 0
        end
        """
        
        result = await self.redis_client.eval(lua_script, 1, key, order_id)
        return result == 1

    async def set_order_id(self, suffix: int, order_id: str) -> bool:
        """
        将已分配后缀绑定到真实订单ID（保持原有TTL）
        仅当后缀键存在时更新其值。
        
        Args:
            suffix: 后缀
            order_id: 订单ID
        Returns:
            是否更新成功
        """
        await self.connect()
        key = f"suffix:{suffix}"
        # 获取剩余TTL
        ttl = await self.redis_client.ttl(key)
        if ttl is None or ttl < 0:
            # -2: 不存在；-1: 无过期
            return False
        # 使用相同TTL重设值
        # Redis 不支持直接保留TTL的SET，因此手动指定 EX
        ok = await self.redis_client.set(key, order_id, ex=max(ttl, 1))
        return ok is True
    
    async def cleanup_expired(self) -> int:
        """
        清理过期的后缀
        
        Returns:
            清理的数量
        """
        await self.connect()
        
        pattern = "suffix:*"
        keys = await self.redis_client.keys(pattern)
        
        # Redis的TTL会自动清理过期的key，这里返回当前活跃的数量
        return len(keys)
    
    async def extend_suffix_lease(self, suffix: int, order_id: str) -> bool:
        """
        延长后缀租期
        
        Args:
            suffix: 后缀
            order_id: 订单ID
            
        Returns:
            是否成功延长
        """
        await self.connect()
        
        key = f"suffix:{suffix}"
        timeout_minutes = get_order_timeout_minutes()
        
        # 使用Lua脚本确保原子性：只有当值匹配时才延长
        lua_script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('EXPIRE', KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        
        result = await self.redis_client.eval(
            lua_script, 1, key, order_id, timeout_minutes * 60
        )
        return result == 1
    
    async def get_suffix_info(self, suffix: int) -> Optional[dict]:
        """
        获取后缀信息
        
        Args:
            suffix: 后缀
            
        Returns:
            后缀信息字典或None
        """
        await self.connect()
        
        key = f"suffix:{suffix}"
        
        # 获取值和TTL
        pipe = self.redis_client.pipeline()
        pipe.get(key)
        pipe.ttl(key)
        results = await pipe.execute()
        
        order_id, ttl = results
        
        if order_id is None:
            return None
        
        return {
            "suffix": suffix,
            "order_id": order_id,
            "ttl_seconds": ttl,
            "expires_at": datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
        }


# 全局实例
suffix_manager = SuffixManager()