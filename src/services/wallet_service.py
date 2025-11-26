"""
钱包服务 - 余额管理

提供用户钱包余额相关的业务逻辑服务。
基于 wallet/wallet_manager.py
"""
from typing import Optional, Tuple
from decimal import Decimal
import logging

from ..database import SessionLocal, User, DebitRecord
from datetime import datetime

logger = logging.getLogger(__name__)


class WalletService:
    """钱包服务类"""
    
    def __init__(self):
        """初始化钱包服务"""
        pass
    
    def get_balance(self, user_id: int) -> Decimal:
        """
        获取用户余额
        
        Args:
            user_id: 用户 ID
            
        Returns:
            余额（USDT）
        """
        try:
            db = SessionLocal()
            user = db.query(User).filter_by(user_id=user_id).first()
            
            if user and user.balance is not None:
                return Decimal(str(user.balance))
            return Decimal("0")
            
        except Exception as e:
            logger.error(f"获取余额失败: user_id={user_id}, {e}")
            return Decimal("0")
        finally:
            db.close()
    
    def increase_balance(
        self,
        user_id: int,
        amount: Decimal,
        reason: str = "",
        order_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        增加用户余额
        
        Args:
            user_id: 用户 ID
            amount: 增加金额
            reason: 原因说明
            order_id: 关联订单 ID
            
        Returns:
            (是否成功, 错误消息)
        """
        if amount <= 0:
            return False, "金额必须大于0"
        
        try:
            db = SessionLocal()
            user = db.query(User).filter_by(user_id=user_id).first()
            
            if not user:
                # 创建新用户
                user = User(user_id=user_id, balance=0)
                db.add(user)
            
            old_balance = Decimal(str(user.balance or 0))
            new_balance = old_balance + amount
            user.balance = float(new_balance)
            
            db.commit()
            
            logger.info(
                f"余额增加: user_id={user_id}, "
                f"amount=+{amount}, "
                f"balance={old_balance}->{new_balance}, "
                f"reason={reason}"
            )
            return True, None
            
        except Exception as e:
            logger.error(f"增加余额失败: user_id={user_id}, {e}")
            return False, str(e)
        finally:
            db.close()
    
    def decrease_balance(
        self,
        user_id: int,
        amount: Decimal,
        reason: str = "",
        order_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        减少用户余额
        
        Args:
            user_id: 用户 ID
            amount: 减少金额
            reason: 原因说明
            order_id: 关联订单 ID
            
        Returns:
            (是否成功, 错误消息)
        """
        if amount <= 0:
            return False, "金额必须大于0"
        
        try:
            db = SessionLocal()
            user = db.query(User).filter_by(user_id=user_id).first()
            
            if not user:
                return False, "用户不存在"
            
            old_balance = Decimal(str(user.balance or 0))
            
            if old_balance < amount:
                return False, f"余额不足（当前: {old_balance}, 需要: {amount}）"
            
            new_balance = old_balance - amount
            user.balance = float(new_balance)
            
            # 记录扣费
            if order_id:
                debit = DebitRecord(
                    user_id=user_id,
                    amount=float(amount),
                    order_type=reason,
                    related_order_id=order_id,
                    created_at=datetime.now()
                )
                db.add(debit)
            
            db.commit()
            
            logger.info(
                f"余额减少: user_id={user_id}, "
                f"amount=-{amount}, "
                f"balance={old_balance}->{new_balance}, "
                f"reason={reason}"
            )
            return True, None
            
        except Exception as e:
            logger.error(f"减少余额失败: user_id={user_id}, {e}")
            return False, str(e)
        finally:
            db.close()
    
    def check_balance(self, user_id: int, required_amount: Decimal) -> Tuple[bool, Decimal]:
        """
        检查余额是否足够
        
        Args:
            user_id: 用户 ID
            required_amount: 需要的金额
            
        Returns:
            (是否足够, 当前余额)
        """
        balance = self.get_balance(user_id)
        return balance >= required_amount, balance
    
    def get_user_info(self, user_id: int) -> Optional[dict]:
        """
        获取用户信息
        
        Args:
            user_id: 用户 ID
            
        Returns:
            用户信息字典或 None
        """
        try:
            db = SessionLocal()
            user = db.query(User).filter_by(user_id=user_id).first()
            
            if not user:
                return None
            
            return {
                "user_id": user.user_id,
                "username": user.username,
                "balance": float(user.balance or 0),
                "is_premium": user.is_premium,
                "premium_expires_at": user.premium_expires_at,
                "created_at": user.created_at,
            }
            
        except Exception as e:
            logger.error(f"获取用户信息失败: user_id={user_id}, {e}")
            return None
        finally:
            db.close()


# 全局服务实例（可选）
wallet_service = WalletService()
