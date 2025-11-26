"""
订单状态管理
订单状态枚举：PENDING、PAID、DELIVERED、PARTIAL、EXPIRED、CANCELLED
幂等更新逻辑（同一 order_id 多次回调仅处理一次）
支持 Premium 订单类型
"""
import asyncio
import logging
from typing import Optional, List
import redis.asyncio as redis
from datetime import datetime, timedelta, timezone
import json
from enum import Enum

from sqlalchemy.orm import sessionmaker

from ..models import Order, OrderStatus, OrderType
from ..database import SessionLocal, Order as DBOrder
from .suffix_manager import suffix_manager
from ..config import settings
from src.common.settings_service import get_order_timeout_minutes


logger = logging.getLogger(__name__)


class OrderManager:
    """订单管理器"""
    
    def __init__(self):
        self.redis_client = None
    
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
    
    # L2 安全加固：后缀分配最大重试次数
    MAX_SUFFIX_RETRY = 5

    async def create_order(
        self, 
        user_id: int, 
        base_amount: float,
        order_type: OrderType = OrderType.OTHER,
        premium_months: Optional[int] = None,
        recipients: Optional[List[str]] = None,
        _retry_count: int = 0
    ) -> Optional[Order]:
        """
        创建新订单
        
        L2 安全加固：若后缀分配重试超过 MAX_SUFFIX_RETRY 次，则返回 None。
        调用方必须检查 None 情况并给用户友好提示。
        
        Args:
            user_id: 用户ID
            base_amount: 基础金额
            order_type: 订单类型
            premium_months: Premium 月数（仅 Premium 订单需要）
            recipients: 收件人列表（仅 Premium 订单需要）
            _retry_count: 内部重试计数（不要外部传入）
            
        Returns:
            创建的订单，或 None（后缀分配失败/重试超限时）
        """
        # L2 安全加固：检查重试次数限制
        if _retry_count >= self.MAX_SUFFIX_RETRY:
            logger.error(f"后缀分配重试次数超限 user={user_id}, retries={_retry_count}")
            return None

        await self.connect()
        
        # 分配唯一后缀
        order_id_temp = f"temp_{user_id}_{int(datetime.now().timestamp())}"
        suffix = await suffix_manager.allocate_suffix(order_id_temp)
        
        if suffix is None:
            return None
        
        # 计算总金额
        from .amount_calculator import AmountCalculator
        total_amount = AmountCalculator.generate_payment_amount(base_amount, suffix)
        
        timeout_minutes = get_order_timeout_minutes()

        # 创建订单
        order = Order(
            base_amount=base_amount,
            unique_suffix=suffix,
            total_amount=total_amount,
            user_id=user_id,
            order_type=order_type,
            premium_months=premium_months,
            recipients=recipients,
            expires_at=datetime.now() + timedelta(minutes=timeout_minutes)
        )

        logger.info(
            "创建订单 %s（类型=%s），超时时间 %s 分钟",
            order.order_id,
            order_type.value if isinstance(order_type, OrderType) else order_type,
            timeout_minutes,
        )
        
        # 更新后缀绑定到真实订单ID
        await suffix_manager.release_suffix(suffix, order_id_temp)
        if not await suffix_manager._reserve_suffix(suffix, order.order_id):
            # 如果重新绑定失败，说明后缀被占用了，重试（带计数）
            return await self.create_order(
                user_id, base_amount, order_type, premium_months, recipients,
                _retry_count=_retry_count + 1
            )
        
        # 保存订单到Redis
        await self._save_order(order, timeout_minutes=timeout_minutes)
        
        return order
    
    async def _save_order(self, order: Order, *, timeout_minutes: Optional[int] = None) -> bool:
        """保存订单到Redis"""
        await self.connect()
        ttl_minutes = timeout_minutes or get_order_timeout_minutes()
        
        order_key = f"order:{order.order_id}"
        amount_key = f"amount:{order.amount_in_micro_usdt}"
        
        # 序列化订单数据
        order_data = order.model_dump()
        order_data["created_at"] = order.created_at.isoformat()
        order_data["updated_at"] = order.updated_at.isoformat()
        order_data["expires_at"] = order.expires_at.isoformat()
        
        pipe = self.redis_client.pipeline()
        
        # 保存订单数据
        pipe.set(
            order_key,
            json.dumps(order_data),
            ex=ttl_minutes * 60 + 300  # 额外5分钟缓冲
        )
        
        # 创建金额到订单ID的映射
        pipe.set(
            amount_key,
            order.order_id,
            ex=ttl_minutes * 60 + 300
        )
        
        results = await pipe.execute()
        return all(results)
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """根据订单ID获取订单"""
        await self.connect()
        
        order_key = f"order:{order_id}"
        order_data = await self.redis_client.get(order_key)
        
        if not order_data:
            return None
        
        try:
            data = json.loads(order_data)
            # 反序列化时间字段
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
            
            return Order(**data)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None
    
    async def find_order_by_amount(self, amount: float) -> Optional[Order]:
        """根据金额查找订单"""
        await self.connect()
        
        # 转换为微USDT
        from .amount_calculator import AmountCalculator
        micro_amount = AmountCalculator.amount_to_micro_usdt(amount)
        amount_key = f"amount:{micro_amount}"
        
        order_id = await self.redis_client.get(amount_key)
        if not order_id:
            return None
        
        return await self.get_order(order_id)
    
    async def update_order_status(
        self, 
        order_id: str, 
        new_status: OrderStatus, 
        tx_hash: str = None,
        delivery_results: dict = None
    ) -> bool:
        """
        幂等更新订单状态
        
        Args:
            order_id: 订单ID
            new_status: 新状态
            tx_hash: 交易哈希（可选）
            delivery_results: 交付结果（仅 Premium 订单）
            
        Returns:
            是否更新成功
        """
        await self.connect()
        
        order = await self.get_order(order_id)
        if not order:
            return False
        
        # 幂等性检查：如果已经是目标状态，直接返回成功
        if order.status == new_status:
            return True
        
        # 状态转换验证
        if not self._is_valid_status_transition(order.status, new_status):
            return False
        
        # 更新状态
        order.update_status(new_status)
        
        # 如果提供了交易哈希，更新订单
        if tx_hash:
            # 这里可以扩展Order模型来包含tx_hash字段
            pass
        
        # 更新交付结果
        if delivery_results:
            order.delivery_results = delivery_results
        
        # 如果订单完成或取消，释放唯一后缀
        if new_status in [OrderStatus.PAID, OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.EXPIRED]:
            await suffix_manager.release_suffix(order.unique_suffix, order_id)
        
        # 保存更新后的订单
        return await self._save_order(order)
    
    def _is_valid_status_transition(self, current: OrderStatus, new: OrderStatus) -> bool:
        """验证状态转换是否有效"""
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.EXPIRED, OrderStatus.CANCELLED],
            OrderStatus.PAID: [OrderStatus.DELIVERED, OrderStatus.PARTIAL],  # 支付后可交付
            OrderStatus.DELIVERED: [],  # 已交付状态不可转换
            OrderStatus.PARTIAL: [OrderStatus.DELIVERED],  # 部分交付可重试变为全部交付
            OrderStatus.EXPIRED: [],  # 已过期状态不可转换
            OrderStatus.CANCELLED: []  # 已取消状态不可转换
        }
        
        return new in valid_transitions.get(current, [])
    
    async def cleanup_expired_orders(self) -> int:
        """清理过期订单"""
        await self.connect()
        
        # 获取所有订单key
        pattern = "order:*"
        keys = await self.redis_client.keys(pattern)
        
        expired_count = 0
        
        for key in keys:
            order_id = key.split(":", 1)[1]
            order = await self.get_order(order_id)
            
            if order and order.is_expired and order.status == OrderStatus.PENDING:
                await self.update_order_status(order_id, OrderStatus.EXPIRED)
                expired_count += 1
        
        return expired_count
    
    async def get_order_statistics(self) -> dict:
        """获取订单统计信息"""
        await self.connect()
        
        pattern = "order:*"
        keys = await self.redis_client.keys(pattern)
        
        stats = {
            "total_orders": 0,
            "pending_orders": 0,
            "paid_orders": 0,
            "delivered_orders": 0,
            "partial_orders": 0,
            "expired_orders": 0,
            "cancelled_orders": 0,
            "active_suffixes": 0
        }
        
        for key in keys:
            order_id = key.split(":", 1)[1]
            order = await self.get_order(order_id)
            
            if order:
                stats["total_orders"] += 1
                if order.status == OrderStatus.PENDING:
                    stats["pending_orders"] += 1
                elif order.status == OrderStatus.PAID:
                    stats["paid_orders"] += 1
                elif order.status == OrderStatus.DELIVERED:
                    stats["delivered_orders"] += 1
                elif order.status == OrderStatus.PARTIAL:
                    stats["partial_orders"] += 1
                elif order.status == OrderStatus.EXPIRED:
                    stats["expired_orders"] += 1
                elif order.status == OrderStatus.CANCELLED:
                    stats["cancelled_orders"] += 1
        
        # 获取活跃后缀数量
        stats["active_suffixes"] = await suffix_manager.cleanup_expired()
        
        return stats


    async def cancel_order(self, order_id: str) -> bool:
        """
        取消订单
        
        Args:
            order_id: 订单ID
            
        Returns:
            是否取消成功
        """
        return await self.update_order_status(order_id, OrderStatus.CANCELLED)


    async def mark_user_confirmed(
        self,
        order_id: str,
        tx_hash: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Optional[DBOrder]:
        """记录用户提供的转账确认信息并持久化至数据库。"""

        return self._mark_user_confirmed_sync(order_id, tx_hash, source)

    def _mark_user_confirmed_sync(
        self,
        order_id: str,
        tx_hash: Optional[str],
        source: Optional[str],
    ) -> Optional[DBOrder]:
        session_factory = SessionLocal
        session = session_factory()
        should_close = isinstance(session_factory, sessionmaker)
        try:
            order = session.query(DBOrder).filter(DBOrder.order_id == order_id).one_or_none()
            if not order:
                return None

            order.user_tx_hash = tx_hash
            order.user_confirm_source = source
            order.user_confirmed_at = datetime.now(timezone.utc)

            session.commit()
            session.refresh(order)
            return order
        finally:
            if should_close:
                session.close()


# 全局实例
order_manager = OrderManager()