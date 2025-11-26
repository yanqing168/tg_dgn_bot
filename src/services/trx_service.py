"""
TRX 兑换服务 - TRX/USDT 兑换业务逻辑

提供 TRX 兑换相关的业务逻辑服务。
基于 legacy/trx_exchange/config.py, rate_manager.py, trx_sender.py
"""
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal
from datetime import datetime
import logging

from ..legacy.trx_exchange.config import TRXExchangeConfig
from ..legacy.trx_exchange.rate_manager import RateManager
from ..legacy.trx_exchange.trx_sender import TRXSender
from ..database import SessionLocal
from ..trx_exchange.models import TRXExchangeOrder

logger = logging.getLogger(__name__)


class TRXService:
    """TRX 兑换服务类"""
    
    def __init__(self, config: Optional[TRXExchangeConfig] = None):
        """
        初始化 TRX 服务
        
        Args:
            config: TRX 兑换配置（可选，用于测试注入）
        """
        self._config = config or TRXExchangeConfig.from_settings()
        self._sender = TRXSender(self._config)
    
    def get_current_rate(self) -> Decimal:
        """
        获取当前 TRX/USDT 汇率
        
        Returns:
            汇率（1 USDT = X TRX）
        """
        try:
            db = SessionLocal()
            rate = RateManager.get_rate(db)
            return rate
        except Exception as e:
            logger.error(f"获取汇率失败: {e}")
            return self._config.default_rate
        finally:
            db.close()
    
    def set_rate(self, new_rate: Decimal, admin_user_id: int) -> Tuple[bool, Optional[str]]:
        """
        设置 TRX/USDT 汇率（管理员操作）
        
        Args:
            new_rate: 新汇率
            admin_user_id: 管理员用户 ID
            
        Returns:
            (是否成功, 错误消息)
        """
        try:
            if new_rate <= 0:
                return False, "汇率必须大于0"
            
            db = SessionLocal()
            RateManager.set_rate(db, new_rate, admin_user_id)
            
            logger.info(f"汇率已更新: {new_rate} (by user {admin_user_id})")
            return True, None
            
        except Exception as e:
            logger.error(f"设置汇率失败: {e}")
            return False, str(e)
        finally:
            db.close()
    
    def calculate_trx_amount(self, usdt_amount: Decimal) -> Dict[str, Any]:
        """
        计算 TRX 兑换金额
        
        Args:
            usdt_amount: USDT 金额
            
        Returns:
            计算结果
        """
        rate = self.get_current_rate()
        trx_amount = RateManager.calculate_trx_amount(usdt_amount, rate)
        
        return {
            "usdt_amount": float(usdt_amount),
            "rate": float(rate),
            "trx_amount": float(trx_amount),
        }
    
    def validate_address(self, address: str) -> bool:
        """
        验证 TRX 地址
        
        Args:
            address: TRX 地址
            
        Returns:
            是否有效
        """
        return self._sender.validate_address(address)
    
    def create_order(
        self,
        user_id: int,
        usdt_amount: Decimal,
        receive_address: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        创建 TRX 兑换订单
        
        Args:
            user_id: 用户 ID
            usdt_amount: USDT 金额
            receive_address: 接收地址
            
        Returns:
            (订单 ID, 错误消息)
        """
        try:
            # 计算 TRX 金额
            calc = self.calculate_trx_amount(usdt_amount)
            rate = Decimal(str(calc["rate"]))
            trx_amount = Decimal(str(calc["trx_amount"]))
            
            # 生成订单 ID
            import uuid
            order_id = f"TRX{uuid.uuid4().hex[:16].upper()}"
            
            # 保存到数据库
            db = SessionLocal()
            try:
                order = TRXExchangeOrder(
                    order_id=order_id,
                    user_id=user_id,
                    usdt_amount=float(usdt_amount),
                    trx_amount=float(trx_amount),
                    rate=float(rate),
                    receive_address=receive_address,
                    status="pending",
                    created_at=datetime.now(),
                )
                db.add(order)
                db.commit()
                
                logger.info(f"创建 TRX 订单: {order_id}, user={user_id}")
                return order_id, None
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"创建 TRX 订单失败: {e}")
            return None, str(e)
    
    def send_trx(
        self,
        order_id: str,
        recipient_address: str,
        amount: Decimal
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        发送 TRX
        
        Args:
            order_id: 订单 ID
            recipient_address: 接收地址
            amount: TRX 金额
            
        Returns:
            (交易哈希, 错误消息)
        """
        try:
            tx_hash = self._sender.send_trx(
                recipient_address=recipient_address,
                amount=amount,
                order_id=order_id,
            )
            
            if tx_hash:
                logger.info(f"TRX 发送成功: order={order_id}, tx={tx_hash}")
                return tx_hash, None
            else:
                return None, "发送失败"
                
        except Exception as e:
            logger.error(f"TRX 发送失败: order={order_id}, {e}")
            return None, str(e)
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        获取订单信息
        
        Args:
            order_id: 订单 ID
            
        Returns:
            订单信息或 None
        """
        try:
            db = SessionLocal()
            order = db.query(TRXExchangeOrder).filter_by(order_id=order_id).first()
            
            if not order:
                return None
            
            return {
                "order_id": order.order_id,
                "user_id": order.user_id,
                "usdt_amount": order.usdt_amount,
                "trx_amount": order.trx_amount,
                "rate": order.rate,
                "receive_address": order.receive_address,
                "status": order.status,
                "tx_hash": order.tx_hash,
                "created_at": order.created_at,
                "completed_at": order.completed_at,
            }
            
        except Exception as e:
            logger.error(f"获取订单失败: {order_id}, {e}")
            return None
        finally:
            db.close()
    
    def update_order_status(
        self,
        order_id: str,
        status: str,
        tx_hash: Optional[str] = None
    ) -> bool:
        """
        更新订单状态
        
        Args:
            order_id: 订单 ID
            status: 新状态
            tx_hash: 交易哈希
            
        Returns:
            是否更新成功
        """
        try:
            db = SessionLocal()
            order = db.query(TRXExchangeOrder).filter_by(order_id=order_id).first()
            
            if not order:
                return False
            
            order.status = status
            if tx_hash:
                order.tx_hash = tx_hash
            if status == "completed":
                order.completed_at = datetime.now()
            
            db.commit()
            logger.info(f"TRX 订单状态更新: {order_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"更新订单状态失败: {order_id}, {e}")
            return False
        finally:
            db.close()
    
    @property
    def is_test_mode(self) -> bool:
        """是否为测试模式"""
        return self._config.test_mode
    
    @property
    def receive_address(self) -> str:
        """获取收款地址"""
        return self._config.receive_address
    
    @property
    def qrcode_file_id(self) -> str:
        """获取二维码文件 ID"""
        return self._config.qrcode_file_id


# 全局服务实例（可选）
trx_service = TRXService()
