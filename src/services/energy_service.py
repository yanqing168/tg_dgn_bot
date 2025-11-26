"""
能量服务 - 能量租赁业务逻辑

提供能量租赁相关的业务逻辑服务。
基于 legacy/energy/manager.py, client.py, models.py
"""
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime
import logging

from ..legacy.energy.models import (
    EnergyOrder,
    EnergyOrderType,
    EnergyOrderStatus,
    EnergyPackage,
    EnergyPriceConfig,
)
from ..legacy.energy.client import EnergyAPIClient, EnergyAPIError
from ..database import SessionLocal, EnergyOrder as DBEnergyOrder

logger = logging.getLogger(__name__)


class EnergyService:
    """能量服务类"""
    
    def __init__(self, api_client: Optional[EnergyAPIClient] = None):
        """
        初始化能量服务
        
        Args:
            api_client: API 客户端（可选，用于测试注入）
        """
        self._api_client = api_client
        self._price_config = EnergyPriceConfig()
    
    @property
    def price_config(self) -> EnergyPriceConfig:
        """获取价格配置"""
        return self._price_config
    
    def get_packages(self) -> List[Dict[str, Any]]:
        """
        获取能量套餐列表
        
        Returns:
            套餐列表
        """
        return [
            {
                "id": "small",
                "name": "6.5万能量",
                "energy_amount": 65000,
                "price_trx": self._price_config.small_energy_price,
                "duration": "1小时",
            },
            {
                "id": "large",
                "name": "13.1万能量",
                "energy_amount": 131000,
                "price_trx": self._price_config.large_energy_price,
                "duration": "1小时",
            },
        ]
    
    def calculate_price(
        self,
        energy_amount: int,
        purchase_count: int = 1
    ) -> Dict[str, Any]:
        """
        计算能量价格
        
        Args:
            energy_amount: 能量数量（65000 或 131000）
            purchase_count: 购买笔数
            
        Returns:
            价格信息
        """
        if energy_amount == 65000:
            unit_price = self._price_config.small_energy_price
        elif energy_amount == 131000:
            unit_price = self._price_config.large_energy_price
        else:
            unit_price = 0
        
        total_price = unit_price * purchase_count
        
        return {
            "energy_amount": energy_amount,
            "purchase_count": purchase_count,
            "unit_price_trx": unit_price,
            "total_price_trx": total_price,
        }
    
    def create_order(
        self,
        user_id: int,
        order_type: EnergyOrderType,
        receive_address: str,
        energy_amount: Optional[int] = None,
        purchase_count: int = 1,
        usdt_amount: Optional[float] = None,
    ) -> Tuple[Optional[EnergyOrder], Optional[str]]:
        """
        创建能量订单
        
        Args:
            user_id: 用户 ID
            order_type: 订单类型
            receive_address: 接收地址
            energy_amount: 能量数量（时长能量用）
            purchase_count: 购买笔数
            usdt_amount: USDT 金额（笔数套餐用）
            
        Returns:
            (订单对象, 错误消息)
        """
        try:
            # 计算价格
            if order_type == EnergyOrderType.HOURLY:
                price_info = self.calculate_price(energy_amount or 65000, purchase_count)
                total_price_trx = price_info["total_price_trx"]
                total_price_usdt = None
            elif order_type == EnergyOrderType.PACKAGE:
                total_price_trx = None
                total_price_usdt = usdt_amount
            else:
                total_price_trx = None
                total_price_usdt = usdt_amount
            
            # 生成订单 ID
            order_id = f"ENERGY_{user_id}_{int(datetime.now().timestamp())}"
            
            # 创建订单对象
            order = EnergyOrder(
                order_id=order_id,
                user_id=user_id,
                order_type=order_type,
                energy_amount=energy_amount,
                purchase_count=purchase_count,
                receive_address=receive_address,
                total_price_trx=total_price_trx,
                total_price_usdt=total_price_usdt,
                status=EnergyOrderStatus.PENDING,
            )
            
            # 保存到数据库
            db = SessionLocal()
            try:
                db_order = DBEnergyOrder(
                    order_id=order.order_id,
                    user_id=order.user_id,
                    order_type=order.order_type.value,
                    energy_amount=order.energy_amount,
                    purchase_count=order.purchase_count,
                    receive_address=order.receive_address,
                    total_price_trx=order.total_price_trx,
                    total_price_usdt=order.total_price_usdt,
                    status=order.status.value,
                )
                db.add(db_order)
                db.commit()
                
                logger.info(f"创建能量订单: {order_id}, user={user_id}")
                return order, None
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"创建能量订单失败: {e}")
            return None, str(e)
    
    def get_order(self, order_id: str) -> Optional[EnergyOrder]:
        """
        获取订单
        
        Args:
            order_id: 订单 ID
            
        Returns:
            订单对象或 None
        """
        try:
            db = SessionLocal()
            db_order = db.query(DBEnergyOrder).filter_by(order_id=order_id).first()
            
            if not db_order:
                return None
            
            return EnergyOrder(
                order_id=db_order.order_id,
                user_id=db_order.user_id,
                order_type=EnergyOrderType(db_order.order_type),
                energy_amount=db_order.energy_amount,
                purchase_count=db_order.purchase_count,
                receive_address=db_order.receive_address,
                total_price_trx=db_order.total_price_trx,
                total_price_usdt=db_order.total_price_usdt,
                status=EnergyOrderStatus(db_order.status),
                api_order_id=db_order.api_order_id,
                error_message=db_order.error_message,
                created_at=db_order.created_at,
                completed_at=db_order.completed_at,
            )
            
        except Exception as e:
            logger.error(f"获取订单失败: {order_id}, {e}")
            return None
        finally:
            db.close()
    
    def update_order_status(
        self,
        order_id: str,
        status: EnergyOrderStatus,
        api_order_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        更新订单状态
        
        Args:
            order_id: 订单 ID
            status: 新状态
            api_order_id: API 订单 ID
            error_message: 错误消息
            
        Returns:
            是否更新成功
        """
        try:
            db = SessionLocal()
            db_order = db.query(DBEnergyOrder).filter_by(order_id=order_id).first()
            
            if not db_order:
                return False
            
            db_order.status = status.value
            if api_order_id:
                db_order.api_order_id = api_order_id
            if error_message:
                db_order.error_message = error_message
            if status == EnergyOrderStatus.COMPLETED:
                db_order.completed_at = datetime.now()
            
            db.commit()
            logger.info(f"订单状态更新: {order_id} -> {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"更新订单状态失败: {order_id}, {e}")
            return False
        finally:
            db.close()
    
    def get_user_orders(self, user_id: int, limit: int = 20) -> List[EnergyOrder]:
        """
        获取用户订单列表
        
        Args:
            user_id: 用户 ID
            limit: 返回数量
            
        Returns:
            订单列表
        """
        try:
            db = SessionLocal()
            db_orders = db.query(DBEnergyOrder).filter_by(
                user_id=user_id
            ).order_by(
                DBEnergyOrder.created_at.desc()
            ).limit(limit).all()
            
            orders = []
            for db_order in db_orders:
                order = EnergyOrder(
                    order_id=db_order.order_id,
                    user_id=db_order.user_id,
                    order_type=EnergyOrderType(db_order.order_type),
                    energy_amount=db_order.energy_amount,
                    purchase_count=db_order.purchase_count,
                    receive_address=db_order.receive_address,
                    total_price_trx=db_order.total_price_trx,
                    total_price_usdt=db_order.total_price_usdt,
                    status=EnergyOrderStatus(db_order.status),
                    api_order_id=db_order.api_order_id,
                    error_message=db_order.error_message,
                    created_at=db_order.created_at,
                    completed_at=db_order.completed_at,
                )
                orders.append(order)
            
            return orders
            
        except Exception as e:
            logger.error(f"获取用户订单失败: {user_id}, {e}")
            return []
        finally:
            db.close()


# 全局服务实例（可选）
energy_service = EnergyService()
