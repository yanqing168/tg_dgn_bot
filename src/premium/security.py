"""
Premium 安全机制
包括：限额控制、黑名单、风险检测等
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db, close_db, PremiumOrder
from ..common.db_manager import get_db_context
from ..config import settings

logger = logging.getLogger(__name__)


class PremiumSecurityConfig:
    """Premium 安全配置"""
    
    # 每日购买限额
    DAILY_PURCHASE_LIMIT = 5  # 每用户每天最多购买5次
    
    # 单笔最大月数
    MAX_MONTHS_PER_ORDER = 12
    
    # 用户名验证超时（秒）
    USERNAME_VERIFY_TIMEOUT = 300  # 5分钟
    
    # 支付确认二次验证
    REQUIRE_PAYMENT_CONFIRMATION = True
    
    # 黑名单功能
    BLACKLIST_ENABLED = True
    
    # 最小间隔时间（秒）
    MIN_ORDER_INTERVAL = 60  # 两次购买至少间隔1分钟
    
    # 异常行为阈值
    SUSPICIOUS_ORDER_COUNT = 10  # 24小时内超过10笔视为异常


class PremiumSecurityService:
    """Premium 安全服务"""
    
    def __init__(self):
        """初始化安全服务"""
        self.config = PremiumSecurityConfig()
        self._blacklist_cache = set()  # 内存黑名单缓存
        self._load_blacklist()
    
    def _load_blacklist(self):
        """加载黑名单"""
        # 从配置文件或数据库加载黑名单
        # 这里使用硬编码示例，实际应从数据库读取
        self._blacklist_cache = set()
        logger.info(f"Loaded {len(self._blacklist_cache)} blacklisted users")
    
    async def check_user_limits(self, user_id: int) -> Dict[str, Any]:
        """
        检查用户购买限额
        
        Args:
            user_id: 用户ID
            
        Returns:
            {
                "allowed": bool,
                "reason": Optional[str],
                "daily_count": int,
                "remaining": int
            }
        """
        with get_db_context() as db:
            # 检查黑名单
            if self.config.BLACKLIST_ENABLED and user_id in self._blacklist_cache:
                return {
                    "allowed": False,
                    "reason": "用户已被限制",
                    "daily_count": 0,
                    "remaining": 0
                }
            
            # 检查订单间隔
            min_interval = timedelta(seconds=self.config.MIN_ORDER_INTERVAL)
            recent_order = db.query(PremiumOrder).filter(
                PremiumOrder.buyer_id == user_id,
                PremiumOrder.status.in_(['PENDING', 'PAID']),
                PremiumOrder.created_at >= datetime.now() - min_interval
            ).order_by(PremiumOrder.created_at.desc()).first()
            
            if recent_order:
                elapsed = (datetime.now() - recent_order.created_at).total_seconds()
                wait_time = int(self.config.MIN_ORDER_INTERVAL - elapsed)
                return {
                    "allowed": False,
                    "reason": f"请等待 {wait_time} 秒后再下单",
                    "daily_count": 0,
                    "remaining": 0
                }
            
            # 检查购买限额
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 查询今日订单数量
            today_orders = db.query(PremiumOrder).filter(
                PremiumOrder.buyer_id == user_id,
                PremiumOrder.created_at >= today_start,
                PremiumOrder.status.in_(['PENDING', 'PAID', 'DELIVERED'])
            ).count()
            
            remaining = max(0, self.config.DAILY_PURCHASE_LIMIT - today_orders)
            
            return {
                "allowed": remaining > 0,
                "reason": "已达到每日购买限额" if remaining == 0 else None,
                "daily_count": today_orders,
                "remaining": remaining
            }
    
    async def check_recipient_limits(self, recipient_username: str) -> Dict[str, Any]:
        """
        检查收件人限制
        
        Args:
            recipient_username: 收件人用户名
            
        Returns:
            {
                "allowed": bool,
                "reason": Optional[str]
            }
        """
        with get_db_context() as db:
            # 检查该收件人今日已接收的Premium数量
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            received_count = db.query(func.count(PremiumOrder.order_id)).filter(
                PremiumOrder.recipient_username == recipient_username,
                PremiumOrder.created_at >= today_start,
                PremiumOrder.status == 'DELIVERED'
            ).scalar()
            
            # 每个收件人每天最多接收3次
            MAX_DAILY_RECEIVE = 3
            if received_count >= MAX_DAILY_RECEIVE:
                return {
                    "allowed": False,
                    "reason": f"该用户今日已接收 {received_count} 次Premium，达到上限"
                }
            
            return {
                "allowed": True,
                "reason": None
            }
    
    async def detect_suspicious_behavior(self, user_id: int) -> Dict[str, Any]:
        """
        检测异常行为
        
        Args:
            user_id: 用户ID
            
        Returns:
            {
                "suspicious": bool,
                "reason": Optional[str],
                "risk_score": int  # 0-100
            }
        """
        with get_db_context() as db:
            # 获取24小时内的订单
            day_ago = datetime.now() - timedelta(hours=24)
            
            recent_orders = db.query(PremiumOrder).filter(
                PremiumOrder.buyer_id == user_id,
                PremiumOrder.created_at >= day_ago
            ).all()
            
            risk_score = 0
            reasons = []
            
            # 检查订单数量
            if len(recent_orders) >= self.config.SUSPICIOUS_ORDER_COUNT:
                risk_score += 30
                reasons.append(f"24小时内订单过多（{len(recent_orders)}笔）")
            
            # 检查是否都是给他人购买
            other_count = sum(1 for o in recent_orders if o.recipient_type == 'other')
            if other_count > 5:
                risk_score += 20
                reasons.append(f"频繁为他人购买（{other_count}次）")
            
            # 检查金额异常
            total_amount = sum(o.amount_usdt for o in recent_orders if o.amount_usdt)
            if total_amount > 200:  # 24小时内超过200 USDT
                risk_score += 25
                reasons.append(f"24小时内总金额过高（${total_amount:.2f}）")
            
            # 检查失败率
            failed_count = sum(1 for o in recent_orders if o.status in ['CANCELLED', 'EXPIRED'])
            if len(recent_orders) > 0:
                fail_rate = failed_count / len(recent_orders)
                if fail_rate > 0.5:
                    risk_score += 15
                    reasons.append(f"订单失败率过高（{fail_rate*100:.0f}%）")
            
            # 检查时间模式（集中在短时间内）
            if len(recent_orders) >= 3:
                time_diffs = []
                sorted_orders = sorted(recent_orders, key=lambda x: x.created_at if x.created_at else datetime.min)
                for i in range(1, len(sorted_orders)):
                    if sorted_orders[i].created_at and sorted_orders[i-1].created_at:
                        diff = (sorted_orders[i].created_at - sorted_orders[i-1].created_at).total_seconds()
                        time_diffs.append(diff)
                
                avg_interval = sum(time_diffs) / len(time_diffs) if time_diffs else 0
                if avg_interval < 300:  # 平均间隔小于5分钟
                    risk_score += 10
                    reasons.append("订单创建过于频繁")
            
            return {
                "suspicious": risk_score >= 50,
                "reason": "; ".join(reasons) if reasons else None,
                "risk_score": min(risk_score, 100)
            }
    
    async def validate_order(
        self,
        user_id: int,
        recipient_username: Optional[str] = None,
        premium_months: int = 0
    ) -> Dict[str, Any]:
        """
        综合验证订单
        
        Args:
            user_id: 购买者ID
            recipient_username: 收件人用户名
            premium_months: 购买月数
            
        Returns:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str]
            }
        """
        errors = []
        warnings = []
        
        # 检查月数限制
        if premium_months > self.config.MAX_MONTHS_PER_ORDER:
            errors.append(f"单笔订单最多购买 {self.config.MAX_MONTHS_PER_ORDER} 个月")
        
        # 检查用户限额
        user_limits = await self.check_user_limits(user_id)
        if not user_limits["allowed"]:
            errors.append(user_limits["reason"])
        elif user_limits["remaining"] <= 2:
            warnings.append(f"今日剩余购买次数：{user_limits['remaining']}")
        
        # 检查收件人限制
        if recipient_username:
            recipient_limits = await self.check_recipient_limits(recipient_username)
            if not recipient_limits["allowed"]:
                errors.append(recipient_limits["reason"])
        
        # 检测异常行为
        behavior = await self.detect_suspicious_behavior(user_id)
        if behavior["suspicious"]:
            warnings.append(f"检测到异常行为：{behavior['reason']}")
            if behavior["risk_score"] >= 70:
                errors.append("风险评分过高，请联系客服")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def add_to_blacklist(self, user_id: int, reason: str = None):
        """
        添加用户到黑名单
        
        Args:
            user_id: 用户ID
            reason: 原因
        """
        self._blacklist_cache.add(user_id)
        logger.warning(f"User {user_id} added to blacklist. Reason: {reason}")
        # TODO: 持久化到数据库
    
    async def remove_from_blacklist(self, user_id: int):
        """
        从黑名单移除用户
        
        Args:
            user_id: 用户ID
        """
        self._blacklist_cache.discard(user_id)
        logger.info(f"User {user_id} removed from blacklist")
        # TODO: 从数据库删除
    
    def is_blacklisted(self, user_id: int) -> bool:
        """
        检查用户是否在黑名单中
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否在黑名单中
        """
        return user_id in self._blacklist_cache


# 全局实例
premium_security = PremiumSecurityService()
