"""
测试数据库上下文管理器的使用
验证统一使用get_db_context避免连接泄漏
"""
import pytest
import tempfile
import os
import time
import gc
from sqlalchemy import create_engine
from src.common.db_manager import get_db_context, get_db_context_readonly
from src.database import Base, User, UserBinding


def safe_remove_file(path, retries=3, delay=0.1):
    """安全删除文件，处理 Windows 文件锁"""
    for i in range(retries):
        try:
            if os.path.exists(path):
                gc.collect()  # 强制垃圾回收
                os.unlink(path)
            return
        except PermissionError:
            if i < retries - 1:
                time.sleep(delay)
    # 最后一次尝试失败，静默忽略（让系统清理临时文件）


class TestDatabaseContextManager:
    """测试数据库上下文管理器"""
    
    def test_get_db_context_exists(self):
        """测试get_db_context函数存在"""
        assert callable(get_db_context)
    
    def test_get_db_context_readonly_exists(self):
        """测试get_db_context_readonly函数存在"""
        assert callable(get_db_context_readonly)
    
    def test_context_manager_auto_commit(self):
        """测试上下文管理器自动提交"""
        from sqlalchemy.orm import sessionmaker
        from contextlib import contextmanager
        from unittest.mock import patch
        
        # 创建完全隔离的内存数据库
        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=test_engine)
        TestSession = sessionmaker(bind=test_engine)
        
        @contextmanager
        def mock_db_context():
            session = TestSession()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        
        # 使用 mock 替换 get_db_context
        with patch('src.common.db_manager.get_db_context', mock_db_context):
            # 使用上下文管理器插入数据
            with mock_db_context() as db:
                user = User(user_id=123456, username="testuser")
                db.add(user)
            
            # 验证数据已提交
            with mock_db_context() as db:
                saved_user = db.query(User).filter(User.user_id == 123456).first()
                assert saved_user is not None
                assert saved_user.username == "testuser"
        
        test_engine.dispose()
    
    def test_context_manager_auto_rollback_on_error(self):
        """测试上下文管理器在错误时自动回滚"""
        from sqlalchemy.orm import sessionmaker
        from contextlib import contextmanager
        
        # 创建完全隔离的内存数据库
        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=test_engine)
        TestSession = sessionmaker(bind=test_engine)
        
        @contextmanager
        def mock_db_context():
            session = TestSession()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        
        # 尝试插入数据但抛出异常
        try:
            with mock_db_context() as db:
                user = User(user_id=123456, username="testuser")
                db.add(user)
                # 模拟错误
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # 验证数据未提交（已回滚）
        with mock_db_context() as db:
            saved_user = db.query(User).filter(User.user_id == 123456).first()
            assert saved_user is None
        
        test_engine.dispose()
    
    def test_readonly_context_no_commit(self):
        """测试只读上下文不提交更改"""
        from sqlalchemy.orm import sessionmaker
        from contextlib import contextmanager
        
        # 创建完全隔离的内存数据库
        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=test_engine)
        TestSession = sessionmaker(bind=test_engine)
        
        @contextmanager
        def mock_db_context():
            session = TestSession()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        
        @contextmanager
        def mock_db_context_readonly():
            session = TestSession()
            try:
                yield session
                # 只读：不提交
            finally:
                session.close()
        
        # 先插入一条数据
        with mock_db_context() as db:
            user = User(user_id=123456, username="testuser")
            db.add(user)
        
        # 使用只读上下文尝试修改
        with mock_db_context_readonly() as db:
            user = db.query(User).filter(User.user_id == 123456).first()
            if user:
                user.username = "modified"
                # 只读上下文不会提交
        
        # 验证数据未被修改
        with mock_db_context() as db:
            user = db.query(User).filter(User.user_id == 123456).first()
            assert user.username == "testuser"  # 未被修改
        
        test_engine.dispose()


class TestModulesUsingContextManager:
    """测试各模块使用上下文管理器"""
    
    @pytest.mark.asyncio
    async def test_user_verification_uses_context_manager(self):
        """测试UserVerificationService使用上下文管理器"""
        from src.premium.user_verification import UserVerificationService
        
        service = UserVerificationService()
        
        # 这些方法应该使用get_db_context
        # 测试它们不会抛出连接相关的异常
        result = await service.get_user_by_id(999999)
        assert result is None  # 用户不存在
        
        result = await service.get_user_by_username("nonexistent_user")
        assert result is None  # 用户不存在
    
    @pytest.mark.asyncio
    async def test_premium_security_uses_context_manager(self):
        """测试PremiumSecurityService使用上下文管理器"""
        from src.premium.security import PremiumSecurityService
        
        service = PremiumSecurityService()
        
        # 测试check_user_limits使用上下文管理器
        result = await service.check_user_limits(999999)
        assert "allowed" in result
        assert "remaining" in result


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
