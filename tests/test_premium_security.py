"""
Premium 安全机制测试
"""
import pytest
import asyncio
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from contextlib import contextmanager

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.premium.security import PremiumSecurityService, PremiumSecurityConfig
from src.database import Base, PremiumOrder
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestPremiumSecurity:
    """Premium安全机制测试"""
    
    @pytest.fixture
    def test_db(self):
        """创建测试数据库"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        return SessionLocal()
    
    @pytest.fixture
    def security_service(self, test_db):
        """创建安全服务实例"""
        # 创建一个返回 test_db 的 context manager
        @contextmanager
        def mock_db_context():
            yield test_db
        
        with patch('src.premium.security.get_db_context', mock_db_context):
            service = PremiumSecurityService()
            yield service
    
    @pytest.mark.asyncio
    async def test_daily_purchase_limit(self, security_service, test_db):
        """测试每日购买限制"""
        user_id = 123456
        
        # 第一次检查，应该允许
        result = await security_service.check_user_limits(user_id)
        assert result["allowed"] is True
        assert result["daily_count"] == 0
        assert result["remaining"] == PremiumSecurityConfig.DAILY_PURCHASE_LIMIT
        
        # 创建达到限额的订单（设置 created_at 为较早时间，避免触发间隔检查）
        for i in range(PremiumSecurityConfig.DAILY_PURCHASE_LIMIT):
            order = PremiumOrder(
                order_id=f"order-{i}",
                buyer_id=user_id,
                recipient_type='self',
                premium_months=3,
                amount_usdt=16.0,
                status='PAID',
                created_at=datetime.now() - timedelta(hours=2, minutes=i*10),  # 2小时前
                expires_at=datetime.now() + timedelta(hours=1)
            )
            test_db.add(order)
        test_db.commit()
        
        # 再次检查，应该不允许
        result = await security_service.check_user_limits(user_id)
        assert result["allowed"] is False
        assert "限额" in result["reason"]
        assert result["daily_count"] == PremiumSecurityConfig.DAILY_PURCHASE_LIMIT
    
    @pytest.mark.asyncio
    async def test_order_interval_check(self, security_service, test_db):
        """测试订单间隔检查"""
        user_id = 123457
        
        # 创建一个刚刚的订单
        recent_order = PremiumOrder(
            order_id="recent-order",
            buyer_id=user_id,
            recipient_type='self',
            premium_months=3,
            amount_usdt=16.0,
            status='PENDING',
            created_at=datetime.now() - timedelta(seconds=30),  # 30秒前
            expires_at=datetime.now() + timedelta(hours=1)
        )
        test_db.add(recent_order)
        test_db.commit()
        
        # 检查限制
        result = await security_service.check_user_limits(user_id)
        assert result["allowed"] is False
        assert "等待" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_blacklist(self, security_service):
        """测试黑名单功能"""
        user_id = 999999
        
        # 初始不在黑名单
        assert security_service.is_blacklisted(user_id) is False
        
        # 添加到黑名单
        await security_service.add_to_blacklist(user_id, "测试原因")
        assert security_service.is_blacklisted(user_id) is True
        
        # 检查限制
        result = await security_service.check_user_limits(user_id)
        assert result["allowed"] is False
        assert "限制" in result["reason"]
        
        # 从黑名单移除
        await security_service.remove_from_blacklist(user_id)
        assert security_service.is_blacklisted(user_id) is False
    
    @pytest.mark.asyncio
    async def test_recipient_limits(self, security_service, test_db):
        """测试收件人限制"""
        recipient_username = "popular_user"
        
        # 创建多个已送达的订单
        for i in range(3):
            order = PremiumOrder(
                order_id=f"gift-{i}",
                buyer_id=100000 + i,
                recipient_username=recipient_username,
                recipient_type='other',
                premium_months=3,
                amount_usdt=16.0,
                status='DELIVERED',
                expires_at=datetime.now() + timedelta(hours=1)
            )
            test_db.add(order)
        test_db.commit()
        
        # 检查限制
        result = await security_service.check_recipient_limits(recipient_username)
        assert result["allowed"] is False
        assert "上限" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_suspicious_behavior_detection(self, security_service, test_db):
        """测试异常行为检测"""
        user_id = 888888
        
        # 创建大量订单
        for i in range(15):
            order = PremiumOrder(
                order_id=f"suspicious-{i}",
                buyer_id=user_id,
                recipient_type='other' if i % 2 == 0 else 'self',
                recipient_username=f"user_{i}" if i % 2 == 0 else None,
                premium_months=12,
                amount_usdt=35.0,
                status='PAID' if i % 3 != 0 else 'CANCELLED',
                created_at=datetime.now() - timedelta(minutes=i*10),
                expires_at=datetime.now() + timedelta(hours=1)
            )
            test_db.add(order)
        test_db.commit()
        
        # 检测异常
        result = await security_service.detect_suspicious_behavior(user_id)
        assert result["suspicious"] is True
        assert result["risk_score"] > 50
        assert result["reason"] is not None
    
    @pytest.mark.asyncio
    async def test_validate_order(self, security_service):
        """测试综合订单验证"""
        user_id = 777777
        
        # 正常订单
        result = await security_service.validate_order(
            user_id=user_id,
            recipient_username="normal_user",
            premium_months=6
        )
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        
        # 超过月数限制的订单
        result = await security_service.validate_order(
            user_id=user_id,
            premium_months=24  # 超过限制
        )
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "最多购买" in result["errors"][0]


@pytest.mark.asyncio
async def test_run_security_ci():
    """运行安全机制CI测试"""
    # 创建测试环境
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    test_db = SessionLocal()
    
    # Mock get_db_context 为返回 test_db 的上下文管理器
    @contextmanager
    def mock_db_context():
        yield test_db
    
    with patch('src.premium.security.get_db_context', mock_db_context):
        with patch('src.premium.security.get_db', return_value=test_db):
            with patch('src.premium.security.close_db'):
                service = PremiumSecurityService()
                
                # 测试黑名单功能
                user_id = 123456
                await service.add_to_blacklist(user_id, "测试")
                assert service.is_blacklisted(user_id)
                
                # 测试用户限额检查
                result = await service.check_user_limits(999999)
                assert result["allowed"] is True
                
                # 测试订单验证
                result = await service.validate_order(
                    user_id=888888,
                    premium_months=3
                )
                assert "valid" in result


if __name__ == "__main__":
    asyncio.run(test_run_security_ci())
