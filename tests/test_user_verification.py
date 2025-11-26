"""
用户验证服务测试
"""
import pytest
import asyncio
import os
import sys
from unittest.mock import MagicMock, patch
from contextlib import contextmanager
from datetime import datetime

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.premium.user_verification import UserVerificationService
from src.database import UserBinding, init_db, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import User


class TestUserVerificationService:
    """用户验证服务测试"""
    
    @pytest.fixture
    def test_db(self):
        """创建测试数据库"""
        # 使用内存数据库 - 每个测试独立
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # 创建返回 session 的 context manager
        @contextmanager
        def mock_db_context():
            yield session
        
        # Mock get_db_context
        with patch('src.premium.user_verification.get_db_context', mock_db_context):
            yield session
                
        # 清理
        session.close()
        engine.dispose()
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return UserVerificationService(bot_username="test_bot")
    
    @pytest.fixture
    def mock_user(self):
        """创建模拟用户"""
        user = MagicMock(spec=User)
        user.id = 123456789
        user.username = "testuser"
        user.first_name = "Test"
        user.last_name = "User"
        return user
    
    @pytest.mark.asyncio
    async def test_bind_user(self, service, test_db, mock_user):
        """测试绑定用户"""
        # 绑定用户
        result = await service.bind_user(mock_user)
        assert result is True
        
        # 验证数据库中有记录
        binding = test_db.query(UserBinding).filter(
            UserBinding.user_id == mock_user.id
        ).first()
        assert binding is not None
        assert binding.username == "testuser"
        assert binding.nickname == "Test"
        assert binding.is_verified is True
    
    @pytest.mark.asyncio
    async def test_verify_user_exists_bound(self, service, test_db, mock_user):
        """测试验证已绑定用户"""
        # 先绑定用户
        await service.bind_user(mock_user)
        
        # 验证用户存在
        result = await service.verify_user_exists("testuser")
        assert result["exists"] is True
        assert result["user_id"] == 123456789
        assert result["nickname"] == "Test"
        assert result["is_verified"] is True
    
    @pytest.mark.asyncio
    async def test_verify_user_not_exists(self, service, test_db):
        """测试验证不存在的用户"""
        result = await service.verify_user_exists("nonexistent")
        assert result["exists"] is False
        assert result["user_id"] is None
        assert result["is_verified"] is False
        assert "t.me/test_bot?start=bind_nonexistent" in result["binding_url"]
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, service, test_db, mock_user):
        """测试通过ID获取用户"""
        # 先绑定用户
        await service.bind_user(mock_user)
        
        # 通过ID获取
        result = await service.get_user_by_id(123456789)
        assert result is not None
        assert result["username"] == "testuser"
        assert result["nickname"] == "Test"
    
    @pytest.mark.asyncio
    async def test_get_user_by_username(self, service, test_db, mock_user):
        """测试通过用户名获取用户"""
        # 先绑定用户
        await service.bind_user(mock_user)
        
        # 通过用户名获取
        result = await service.get_user_by_username("testuser")
        assert result is not None
        assert result["user_id"] == 123456789
        assert result["nickname"] == "Test"
    
    @pytest.mark.asyncio
    async def test_bind_user_without_username(self, service, test_db):
        """测试绑定没有用户名的用户"""
        user = MagicMock(spec=User)
        user.id = 987654321
        user.username = None
        user.first_name = "NoUsername"
        
        result = await service.bind_user(user)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_bind_user_force_update(self, service, test_db, mock_user):
        """测试强制更新绑定"""
        # 第一次绑定
        await service.bind_user(mock_user)
        
        # 修改用户信息
        mock_user.first_name = "Updated"
        
        # 强制更新
        result = await service.bind_user(mock_user, force_update=True)
        assert result is True
        
        # 验证更新
        binding = test_db.query(UserBinding).filter(
            UserBinding.user_id == mock_user.id
        ).first()
        assert binding.nickname == "Updated"
    
    @pytest.mark.asyncio
    async def test_auto_bind_on_interaction(self, service, test_db, mock_user):
        """测试自动绑定"""
        # 自动绑定
        await service.auto_bind_on_interaction(mock_user)
        
        # 验证绑定成功
        binding = test_db.query(UserBinding).filter(
            UserBinding.user_id == mock_user.id
        ).first()
        assert binding is not None
        assert binding.username == "testuser"


@pytest.mark.asyncio
async def test_run_verification_ci():
    """运行验证服务CI测试"""
    print("\n" + "="*80)
    print(" 用户验证服务 CI 测试 ".center(80, "="))
    print("="*80)
    
    # 创建测试实例
    test_instance = TestUserVerificationService()
    
    # 创建测试数据库
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    
    # Mock get_db 和 close_db
    with patch('src.premium.user_verification.get_db') as mock_get_db:
        with patch('src.premium.user_verification.close_db') as mock_close_db:
            mock_get_db.return_value = SessionLocal()
            mock_close_db.return_value = None
            
            # 运行测试
            service = UserVerificationService(bot_username="test_bot")
            test_db = SessionLocal()
            
            # 创建模拟用户
            mock_user = MagicMock(spec=User)
            mock_user.id = 123456789
            mock_user.username = "testuser"
            mock_user.first_name = "Test"
            
            # 测试绑定
            print("\n[测试] 绑定用户...")
            result = await service.bind_user(mock_user)
            assert result is True
            print("✅ 绑定成功")
            
            # 测试验证
            print("[测试] 验证用户存在...")
            result = await service.verify_user_exists("testuser")
            assert result["exists"] is True
            print("✅ 验证成功")
            
            # 测试查询
            print("[测试] 通过ID查询...")
            result = await service.get_user_by_id(123456789)
            assert result is not None
            print("✅ 查询成功")
            
            print("\n" + "-"*80)
            print(" 用户验证服务测试通过 ✅ ".center(80))
            print("-"*80)


if __name__ == "__main__":
    asyncio.run(test_run_verification_ci())
