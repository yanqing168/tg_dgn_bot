"""
能量订单管理器
处理订单创建、状态更新、余额扣费等

[Legacy] 旧版实现，仅用于兼容，后续会被 services 层封装替代
"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from loguru import logger

from ...database import EnergyOrder as DBEnergyOrder, User, DebitRecord, get_db, close_db
from ...wallet.wallet_manager import WalletManager
from .models import (
    EnergyOrder,
    EnergyOrderType,
    EnergyOrderStatus,
    EnergyPackage,
    EnergyPriceConfig,
)
from .client import EnergyAPIClient, EnergyAPIError


class EnergyOrderManager:
    """能量订单管理器"""
    
    def __init__(self, api_client: EnergyAPIClient, wallet_manager: WalletManager):
        """
        初始化管理器
        
        Args:
            api_client: API客户端
            wallet_manager: 钱包管理器
        """
        self.api = api_client
        self.wallet = wallet_manager
        self.price_config = EnergyPriceConfig()
    
    async def create_hourly_order(
        self,
        user_id: int,
        receive_address: str,
        energy_package: EnergyPackage,
        purchase_count: int = 1
    ) -> EnergyOrder:
        """
        创建时长能量订单
        
        Args:
            user_id: 用户ID
            receive_address: 接收地址
            energy_package: 能量套餐(65000/131000)
            purchase_count: 购买笔数(1-20)
        
        Returns:
            能量订单
        
        Raises:
            ValueError: 参数错误
        """
        # 验证参数
        if purchase_count < 1 or purchase_count > self.price_config.max_purchases:
            raise ValueError(f"购买笔数必须在1-{self.price_config.max_purchases}之间")
        
        # 计算价格
        energy_amount = int(energy_package.value)
        if energy_amount == 65000:
            unit_price = self.price_config.small_energy_price
        elif energy_amount == 131000:
            unit_price = self.price_config.large_energy_price
        else:
            raise ValueError("不支持的能量套餐")
        
        total_price_trx = unit_price * purchase_count
        
        # 生成订单ID
        order_id = f"ENERGY_{user_id}_{int(datetime.now().timestamp())}"
        
        # 创建订单对象
        order = EnergyOrder(
            order_id=order_id,
            user_id=user_id,
            order_type=EnergyOrderType.HOURLY,
            energy_amount=energy_amount,
            purchase_count=purchase_count,
            receive_address=receive_address,
            total_price_trx=total_price_trx,
            status=EnergyOrderStatus.PENDING,
        )
        
        # 保存到数据库
        db = get_db()
        try:
            db_order = DBEnergyOrder(
                order_id=order.order_id,
                user_id=order.user_id,
                order_type=order.order_type.value,
                energy_amount=order.energy_amount,
                purchase_count=order.purchase_count,
                receive_address=order.receive_address,
                total_price_trx=order.total_price_trx,
                status=order.status.value,
            )
            db.add(db_order)
            db.commit()
            db.refresh(db_order)
            
            logger.info(f"创建时长能量订单: {order_id}, 用户: {user_id}, 金额: {total_price_trx} TRX")
            
            return order
        finally:
            close_db(db)
    
    async def create_package_order(
        self,
        user_id: int,
        receive_address: str,
        usdt_amount: float
    ) -> EnergyOrder:
        """
        创建笔数套餐订单
        
        Args:
            user_id: 用户ID
            receive_address: 接收地址
            usdt_amount: USDT金额
        
        Returns:
            能量订单
        
        Raises:
            ValueError: 参数错误
        """
        # 验证金额
        if usdt_amount < self.price_config.package_min_usdt:
            raise ValueError(f"最低充值金额为 {self.price_config.package_min_usdt} USDT")
        
        # 计算笔数（USDT转TRX按1:7汇率估算，仅供参考）
        # 实际计算由API返回
        estimated_trx = usdt_amount * 7
        estimated_count = int(estimated_trx / self.price_config.package_price_per_tx)
        
        # 生成订单ID
        order_id = f"PACKAGE_{user_id}_{int(datetime.now().timestamp())}"
        
        # 创建订单对象
        order = EnergyOrder(
            order_id=order_id,
            user_id=user_id,
            order_type=EnergyOrderType.PACKAGE,
            package_count=estimated_count,
            receive_address=receive_address,
            total_price_usdt=usdt_amount,
            status=EnergyOrderStatus.PENDING,
        )
        
        # 保存到数据库
        db = get_db()
        try:
            db_order = DBEnergyOrder(
                order_id=order.order_id,
                user_id=order.user_id,
                order_type=order.order_type.value,
                package_count=order.package_count,
                receive_address=order.receive_address,
                total_price_usdt=order.total_price_usdt,
                status=order.status.value,
            )
            db.add(db_order)
            db.commit()
            db.refresh(db_order)
            
            logger.info(f"创建笔数套餐订单: {order_id}, 用户: {user_id}, 金额: {usdt_amount} USDT")
            
            return order
        finally:
            close_db(db)
    
    async def process_order(self, order_id: str) -> bool:
        """
        处理订单（调用API购买）
        
        Args:
            order_id: 订单ID
        
        Returns:
            是否成功
        """
        db = get_db()
        try:
            # 查询订单
            db_order = db.query(DBEnergyOrder).filter_by(order_id=order_id).first()
            if not db_order:
                logger.error(f"订单不存在: {order_id}")
                return False
            
            # 检查状态
            if db_order.status != EnergyOrderStatus.PENDING.value:
                logger.warning(f"订单状态不是PENDING: {order_id}, 状态: {db_order.status}")
                return False
            
            # 更新状态为处理中
            db_order.status = EnergyOrderStatus.PROCESSING.value
            db.commit()
            
            try:
                # 根据订单类型调用API
                if db_order.order_type == EnergyOrderType.HOURLY.value:
                    # 时长能量
                    response = await self.api.buy_energy(
                        receive_address=db_order.receive_address,
                        energy_amount=db_order.energy_amount,
                        rent_time=1
                    )
                    
                elif db_order.order_type == EnergyOrderType.PACKAGE.value:
                    # 笔数套餐
                    response = await self.api.buy_package(
                        receive_address=db_order.receive_address
                    )
                    
                else:
                    raise ValueError(f"不支持的订单类型: {db_order.order_type}")
                
                # 更新订单
                db_order.api_order_id = response.order_id
                db_order.status = EnergyOrderStatus.COMPLETED.value
                db_order.completed_at = datetime.now()
                db.commit()
                
                logger.info(f"订单处理成功: {order_id}, API订单ID: {response.order_id}")
                return True
                
            except EnergyAPIError as e:
                # API错误
                logger.error(f"API错误: {e.code} - {e.message}")
                
                db_order.status = EnergyOrderStatus.FAILED.value
                db_order.error_message = f"{e.code}: {e.message}"
                db.commit()
                
                return False
            
        finally:
            close_db(db)
    
    async def pay_with_balance(self, order_id: str) -> tuple[bool, Optional[str]]:
        """
        使用余额支付订单
        
        Args:
            order_id: 订单ID
        
        Returns:
            (是否成功, 错误信息)
        """
        db = get_db()
        try:
            # 查询订单
            db_order = db.query(DBEnergyOrder).filter_by(order_id=order_id).first()
            if not db_order:
                return False, "订单不存在"
            
            # 检查状态
            if db_order.status != EnergyOrderStatus.PENDING.value:
                return False, f"订单状态错误: {db_order.status}"
            
            # 计算需要扣费的金额（TRX转USDT按1:7汇率）
            if db_order.total_price_trx:
                amount_usdt = db_order.total_price_trx / 7.0
            elif db_order.total_price_usdt:
                amount_usdt = db_order.total_price_usdt
            else:
                return False, "订单金额错误"
            
            # 扣费
            success, error = await self.wallet.debit(
                user_id=db_order.user_id,
                amount=amount_usdt,
                order_type="energy",
                related_order_id=order_id
            )
            
            if not success:
                return False, error
            
            # 处理订单（调用API）
            process_success = await self.process_order(order_id)
            
            if not process_success:
                # 处理失败，退款
                logger.warning(f"订单处理失败，退款: {order_id}")
                # TODO: 实现退款逻辑
                return False, "能量购买失败，请联系客服退款"
            
            return True, None
            
        finally:
            close_db(db)
    
    async def query_user_orders(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[EnergyOrder]:
        """
        查询用户订单
        
        Args:
            user_id: 用户ID
            limit: 返回数量
        
        Returns:
            订单列表
        """
        db = get_db()
        try:
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
                    package_count=db_order.package_count,
                    usdt_amount=db_order.usdt_amount,
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
            
        finally:
            close_db(db)
    
    async def get_order(self, order_id: str) -> Optional[EnergyOrder]:
        """
        获取订单
        
        Args:
            order_id: 订单ID
        
        Returns:
            订单对象或None
        """
        db = get_db()
        try:
            db_order = db.query(DBEnergyOrder).filter_by(order_id=order_id).first()
            if not db_order:
                return None
            
            return EnergyOrder(
                order_id=db_order.order_id,
                user_id=db_order.user_id,
                order_type=EnergyOrderType(db_order.order_type),
                energy_amount=db_order.energy_amount,
                purchase_count=db_order.purchase_count,
                package_count=db_order.package_count,
                usdt_amount=db_order.usdt_amount,
                receive_address=db_order.receive_address,
                total_price_trx=db_order.total_price_trx,
                total_price_usdt=db_order.total_price_usdt,
                status=EnergyOrderStatus(db_order.status),
                api_order_id=db_order.api_order_id,
                error_message=db_order.error_message,
                created_at=db_order.created_at,
                completed_at=db_order.completed_at,
            )
            
        finally:
            close_db(db)
