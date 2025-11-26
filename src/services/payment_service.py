"""
支付服务 - 支付相关业务逻辑

提供支付相关的业务逻辑服务。
基于 payments/suffix_manager.py, amount_calculator.py, order.py, payment_processor.py
"""
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal
from datetime import datetime
import logging

from ..payments.suffix_manager import suffix_manager
from ..payments.order import order_manager
from ..database import SessionLocal

logger = logging.getLogger(__name__)


class PaymentService:
    """支付服务类"""
    
    def __init__(self):
        """初始化支付服务"""
        pass
    
    def generate_unique_amount(
        self,
        base_amount: Decimal,
        order_id: str
    ) -> Tuple[Optional[Decimal], Optional[str]]:
        """
        生成唯一金额（带后缀）
        
        Args:
            base_amount: 基础金额
            order_id: 订单 ID
            
        Returns:
            (唯一金额, 错误消息)
        """
        try:
            # 分配后缀
            suffix = suffix_manager.allocate(order_id)
            
            if suffix is None:
                return None, "后缀池已满，请稍后重试"
            
            # 计算唯一金额
            unique_amount = base_amount + suffix
            
            logger.info(f"生成唯一金额: order={order_id}, base={base_amount}, suffix={suffix}, unique={unique_amount}")
            return unique_amount, None
            
        except Exception as e:
            logger.error(f"生成唯一金额失败: {e}")
            return None, str(e)
    
    def release_suffix(self, order_id: str) -> bool:
        """
        释放后缀（订单完成或取消时）
        
        Args:
            order_id: 订单 ID
            
        Returns:
            是否释放成功
        """
        try:
            suffix_manager.release(order_id)
            logger.info(f"释放后缀: order={order_id}")
            return True
        except Exception as e:
            logger.error(f"释放后缀失败: {order_id}, {e}")
            return False
    
    def create_payment_order(
        self,
        user_id: int,
        order_type: str,
        amount: Decimal,
        related_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        创建支付订单
        
        Args:
            user_id: 用户 ID
            order_type: 订单类型
            amount: 金额
            related_data: 关联数据
            
        Returns:
            (订单 ID, 错误消息)
        """
        try:
            order_id = order_manager.create_order(
                user_id=user_id,
                order_type=order_type,
                amount=float(amount),
                data=related_data
            )
            
            logger.info(f"创建支付订单: order={order_id}, user={user_id}, type={order_type}")
            return order_id, None
            
        except Exception as e:
            logger.error(f"创建支付订单失败: {e}")
            return None, str(e)
    
    def confirm_payment(
        self,
        order_id: str,
        tx_hash: Optional[str] = None,
        payment_method: str = "transfer"
    ) -> Tuple[bool, Optional[str]]:
        """
        确认支付
        
        Args:
            order_id: 订单 ID
            tx_hash: 交易哈希
            payment_method: 支付方式
            
        Returns:
            (是否成功, 错误消息)
        """
        try:
            success = order_manager.confirm_payment(
                order_id=order_id,
                tx_hash=tx_hash,
                payment_method=payment_method
            )
            
            if success:
                # 释放后缀
                self.release_suffix(order_id)
                logger.info(f"支付确认成功: order={order_id}")
                return True, None
            else:
                return False, "支付确认失败"
                
        except Exception as e:
            logger.error(f"支付确认失败: {order_id}, {e}")
            return False, str(e)
    
    def cancel_order(self, order_id: str, reason: str = "") -> Tuple[bool, Optional[str]]:
        """
        取消订单
        
        Args:
            order_id: 订单 ID
            reason: 取消原因
            
        Returns:
            (是否成功, 错误消息)
        """
        try:
            success = order_manager.cancel_order(order_id, reason)
            
            if success:
                # 释放后缀
                self.release_suffix(order_id)
                logger.info(f"订单取消成功: order={order_id}, reason={reason}")
                return True, None
            else:
                return False, "取消订单失败"
                
        except Exception as e:
            logger.error(f"取消订单失败: {order_id}, {e}")
            return False, str(e)
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        获取订单状态
        
        Args:
            order_id: 订单 ID
            
        Returns:
            订单状态信息或 None
        """
        try:
            return order_manager.get_order(order_id)
        except Exception as e:
            logger.error(f"获取订单状态失败: {order_id}, {e}")
            return None
    
    def expire_old_orders(self, timeout_minutes: int = 30) -> int:
        """
        过期旧订单
        
        Args:
            timeout_minutes: 超时时间（分钟）
            
        Returns:
            过期的订单数量
        """
        try:
            count = order_manager.expire_orders(timeout_minutes)
            logger.info(f"过期订单: count={count}, timeout={timeout_minutes}min")
            return count
        except Exception as e:
            logger.error(f"过期订单失败: {e}")
            return 0
    
    def get_pending_orders_count(self) -> int:
        """
        获取待支付订单数量
        
        Returns:
            订单数量
        """
        try:
            return order_manager.get_pending_count()
        except Exception as e:
            logger.error(f"获取待支付订单数量失败: {e}")
            return 0


# 全局服务实例（可选）
payment_service = PaymentService()
