"""
健康检查模块

提供 /health 命令：检查 Redis 与数据库可用性。
也提供可测试的 HealthService，用于在单元测试中注入假客户端。
"""
from __future__ import annotations

from typing import Optional, Tuple, Callable, Dict, Any
import asyncio

from .config import settings
from .database import get_db, close_db


class HealthService:
    """健康检查服务。"""

    def __init__(self):
        self._redis_mod = None  # 延迟导入 redis.asyncio，避免测试时强依赖

    def _get_redis_module(self):
        if self._redis_mod is None:
            import redis.asyncio as redis  # type: ignore
            self._redis_mod = redis
        return self._redis_mod

    async def check_redis(self, redis_client=None) -> Tuple[bool, str]:
        """检查 Redis 连接。

        Args:
            redis_client: 可注入的 redis 客户端，需实现 async ping()
        Returns:
            (ok, message)
        """
        try:
            client = redis_client
            if client is None:
                redis = self._get_redis_module()
                client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    decode_responses=True,
                )
            pong = await client.ping()
            return bool(pong), "Redis OK" if pong else "Redis ping failed"
        except Exception as e:
            return False, f"Redis error: {e}"

    def check_db(self, session_factory: Optional[Callable[[], Any]] = None) -> Tuple[bool, str]:
        """检查数据库连通性（执行 SELECT 1）。

        Args:
            session_factory: 可注入的会话工厂，返回对象需有 execute()/close()
        Returns:
            (ok, message)
        """
        try:
            db = session_factory() if session_factory else get_db()
            try:
                # 使用简单查询验证连接
                from sqlalchemy import text
                db.execute(text("SELECT 1"))
                return True, "DB OK"
            finally:
                if session_factory is None:
                    close_db(db)
                else:
                    # 假会话可能没有 close
                    close = getattr(db, "close", None)
                    if callable(close):
                        close()
        except Exception as e:
            return False, f"DB error: {e}"

    async def check_all(self, redis_client=None, session_factory: Optional[Callable[[], Any]] = None) -> Dict[str, Any]:
        """综合检查 Redis 与 DB。

        Returns:
            {'redis': {'ok': bool, 'msg': str}, 'db': {'ok': bool, 'msg': str}, 'ok': bool}
        """
        redis_ok, redis_msg = await self.check_redis(redis_client)
        db_ok, db_msg = self.check_db(session_factory)
        return {
            'redis': {'ok': redis_ok, 'msg': redis_msg},
            'db': {'ok': db_ok, 'msg': db_msg},
            'ok': redis_ok and db_ok,
        }


health_service = HealthService()


async def health_command(update, context):
    """/health 命令处理器：输出 Redis/DB 状态。"""
    user = update.effective_user
    if not user or user.id != settings.bot_owner_id:
        if update.message:
            await update.message.reply_text("⛔ 仅机器人拥有者可使用此命令。")
        return

    result = await health_service.check_all()
    status_emoji = "✅" if result['ok'] else "❌"
    text = (
        f"{status_emoji} <b>健康检查</b>\n\n"
        f"Redis: {'✅' if result['redis']['ok'] else '❌'} - {result['redis']['msg']}\n"
        f"DB: {'✅' if result['db']['ok'] else '❌'} - {result['db']['msg']}\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")
