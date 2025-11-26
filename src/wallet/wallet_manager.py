"""
钱包管理器
处理用户余额、充值、扣费等操作
"""
from typing import Optional, Tuple
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_
import uuid

from ..database import User, DepositOrder, DebitRecord, get_db, close_db
from src.common.settings_service import get_order_timeout_minutes


logger = logging.getLogger(__name__)


class WalletManager:
    """钱包管理器"""
    
    def __init__(self, db: Optional[Session] = None):
        """初始化钱包管理器
        
        Args:
            db: 数据库会话，如果为None则自动创建
        """
        self.db = db
        self._auto_close = db is None
    
    def _get_db(self) -> Session:
        """获取数据库会话"""
        if self.db is None:
            self.db = get_db()
        return self.db
    
    def close(self):
        """关闭数据库会话"""
        if self._auto_close and self.db:
            close_db(self.db)
            self.db = None
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    def get_or_create_user(self, user_id: int, username: Optional[str] = None) -> User:
        """获取或创建用户
        
        Args:
            user_id: Telegram用户ID
            username: 用户名（可选）
        
        Returns:
            User对象
        """
        db = self._get_db()
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            user = User(user_id=user_id, username=username, balance_micro_usdt=0)
            db.add(user)
            db.commit()
            db.refresh(user)
        elif username and user.username != username:
            user.username = username
            db.commit()
        
        return user
    
    def get_balance(self, user_id: int) -> float:
        """查询用户余额
        
        Args:
            user_id: 用户ID
        
        Returns:
            余额（USDT）
        """
        user = self.get_or_create_user(user_id)
        return user.get_balance()
    
    def create_deposit_order(
        self,
        user_id: int,
        base_amount: float,
        unique_suffix: int,
        timeout_minutes: Optional[int] = None
    ) -> DepositOrder:
        """创建充值订单
        
        Args:
            user_id: 用户ID
            base_amount: 基础金额
            unique_suffix: 唯一后缀 (1-999)
            timeout_minutes: 超时时间（分钟）
        
        Returns:
            充值订单对象
        """
        db = self._get_db()
        
        # 确保用户存在
        self.get_or_create_user(user_id)
        
        # 计算总金额
        total_amount = base_amount + unique_suffix / 1000
        amount_micro_usdt = int(total_amount * 1_000_000)
        
        effective_timeout = timeout_minutes or get_order_timeout_minutes()

        # 创建订单
        order = DepositOrder(
            order_id=str(uuid.uuid4()),
            user_id=user_id,
            base_amount=base_amount,
            unique_suffix=unique_suffix,
            total_amount=total_amount,
            amount_micro_usdt=amount_micro_usdt,
            status="PENDING",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=effective_timeout)
        )
        
        db.add(order)
        db.commit()
        db.refresh(order)

        logger.info(
            "创建充值订单 %s（用户=%s），超时时间 %s 分钟",
            order.order_id,
            user_id,
            effective_timeout,
        )

        return order
    
    def process_deposit_callback(
        self,
        order_id: str,
        amount: float,
        tx_hash: str
    ) -> Tuple[bool, str]:
        """处理充值回调（幂等）
        
        Args:
            order_id: 订单ID
            amount: 支付金额
            tx_hash: 交易哈希
        
        Returns:
            (成功, 消息)
        """
        db = self._get_db()
        
        # 查询订单
        order = db.query(DepositOrder).filter(
            DepositOrder.order_id == order_id
        ).first()
        
        if not order:
            return False, f"订单不存在: {order_id}"
        
        # 检查是否已支付（幂等）
        if order.status == "PAID":
            return True, "订单已处理（幂等）"
        
        # 检查是否过期
        if datetime.now() > order.expires_at:
            order.status = "EXPIRED"
            db.commit()
            return False, "订单已过期"
        
        # 金额匹配（使用整数化比较）
        paid_micro_usdt = int(amount * 1_000_000)
        if paid_micro_usdt != order.amount_micro_usdt:
            return False, f"金额不匹配: 期望 {order.total_amount:.3f} USDT, 实际 {amount:.3f} USDT"
        
        # 更新订单状态
        order.status = "PAID"
        order.tx_hash = tx_hash
        order.paid_at = datetime.now()
        
        # 用户余额入账
        user = db.query(User).filter(User.user_id == order.user_id).first()
        if not user:
            db.rollback()
            return False, "用户不存在"
        
        user.balance_micro_usdt += order.amount_micro_usdt
        user.updated_at = datetime.now()
        
        db.commit()
        
        return True, f"充值成功: +{order.total_amount:.3f} USDT"
    
    def debit(
        self,
        user_id: int,
        amount: float,
        order_type: str,
        related_order_id: Optional[str] = None
    ) -> bool:
        """扣费（余额不足则拒绝）
        
        M5 安全加固：使用事务确保扣费和流水记录原子性
        
        Args:
            user_id: 用户ID
            amount: 扣费金额（USDT）
            order_type: 订单类型
            related_order_id: 关联订单ID
        
        Returns:
            是否扣费成功
        """
        db = self._get_db()
        
        try:
            # 获取用户（加锁防止并发）
            user = db.query(User).filter(User.user_id == user_id).with_for_update().first()
            
            if not user:
                return False
            
            # 计算微USDT金额
            amount_micro_usdt = int(amount * 1_000_000)
            
            # 检查余额
            if user.balance_micro_usdt < amount_micro_usdt:
                return False
            
            # 扣费
            user.balance_micro_usdt -= amount_micro_usdt
            user.updated_at = datetime.now()
            
            # 记录扣费（与扣费在同一事务中）
            record = DebitRecord(
                user_id=user_id,
                amount_micro_usdt=amount_micro_usdt,
                order_type=order_type,
                related_order_id=related_order_id
            )
            db.add(record)
            
            # 原子提交：扣费 + 流水记录
            db.commit()
            return True
            
        except Exception as e:
            # M5：异常时回滚，确保不会出现"扣费成功但流水失败"
            db.rollback()
            logger.error(f"扣费失败 user={user_id} amount={amount}: {e}")
            return False
    
    def get_deposit_order(self, order_id: str) -> Optional[DepositOrder]:
        """查询充值订单
        
        Args:
            order_id: 订单ID
        
        Returns:
            充值订单对象或None
        """
        db = self._get_db()
        return db.query(DepositOrder).filter(
            DepositOrder.order_id == order_id
        ).first()
    
    def get_user_deposits(self, user_id: int, limit: int = 10) -> list:
        """查询用户充值记录
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
        
        Returns:
            充值订单列表
        """
        db = self._get_db()
        return db.query(DepositOrder).filter(
            DepositOrder.user_id == user_id
        ).order_by(DepositOrder.created_at.desc()).limit(limit).all()
    
    def get_user_debits(self, user_id: int, limit: int = 10) -> list:
        """查询用户扣费记录
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
        
        Returns:
            扣费记录列表
        """
        db = self._get_db()
        return db.query(DebitRecord).filter(
            DebitRecord.user_id == user_id
        ).order_by(DebitRecord.created_at.desc()).limit(limit).all()


# 创建全局实例（用于简单场景）
def get_wallet_manager() -> WalletManager:
    """获取钱包管理器实例"""
    return WalletManager()
