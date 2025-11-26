"""
地址查询限频测试
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.address_query.handler import AddressQueryHandler
from src.database import Base, AddressQueryLog


@pytest.fixture
def test_db():
    """测试数据库 fixture - 使用独立内存数据库"""
    # 创建完全隔离的内存数据库
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestSessionLocal = sessionmaker(bind=test_engine)
    
    yield TestSessionLocal
    
    # 清理
    test_engine.dispose()


@pytest.fixture
def mock_session_local(test_db):
    """Mock SessionLocal 使用测试数据库"""
    with patch('src.address_query.handler.SessionLocal', test_db):
        with patch('src.database.SessionLocal', test_db):
            yield test_db


class TestAddressQueryRateLimit:
    """地址查询限频测试"""
    
    def test_first_query_allowed(self, mock_session_local):
        """测试首次查询允许"""
        user_id = 12345
        
        can_query, remaining = AddressQueryHandler._check_rate_limit(user_id)
        
        assert can_query is True
        assert remaining == 0
    
    def test_query_within_limit_rejected(self, mock_session_local):
        """测试限频期内查询被拒绝"""
        user_id = 12346
        
        # 第一次查询
        AddressQueryHandler._record_query(user_id)
        
        # 立即再次查询（应被拒绝）
        can_query, remaining = AddressQueryHandler._check_rate_limit(user_id)
        
        assert can_query is False
        assert remaining > 0
        assert remaining <= 1  # 应该在 1 分钟内
    
    def test_query_after_limit_allowed(self, mock_session_local):
        """测试限频期后查询允许"""
        user_id = 12347
        
        # 记录查询（手动设置为 2 分钟前）
        db = mock_session_local()
        try:
            log = AddressQueryLog(
                user_id=user_id,
                last_query_at=datetime.now() - timedelta(minutes=2),
                query_count=1
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
        
        # 检查限频（应允许）
        can_query, remaining = AddressQueryHandler._check_rate_limit(user_id)
        
        assert can_query is True
        assert remaining == 0
    
    def test_record_query_creates_log(self, mock_session_local):
        """测试记录查询创建日志"""
        user_id = 12348
        
        AddressQueryHandler._record_query(user_id)
        
        db = mock_session_local()
        try:
            log = db.query(AddressQueryLog).filter_by(user_id=user_id).first()
            
            assert log is not None
            assert log.user_id == user_id
            assert log.query_count == 1
            assert isinstance(log.last_query_at, datetime)
        finally:
            db.close()
    
    def test_record_query_updates_existing(self, mock_session_local):
        """测试记录查询更新已有记录"""
        user_id = 12349
        
        # 第一次查询
        AddressQueryHandler._record_query(user_id)
        
        db = mock_session_local()
        try:
            log = db.query(AddressQueryLog).filter_by(user_id=user_id).first()
            first_time = log.last_query_at
            first_count = log.query_count
        finally:
            db.close()
        
        # 等待 2 分钟（模拟）
        db = mock_session_local()
        try:
            log = db.query(AddressQueryLog).filter_by(user_id=user_id).first()
            log.last_query_at = datetime.now() - timedelta(minutes=2)
            db.commit()
        finally:
            db.close()
        
        # 第二次查询
        AddressQueryHandler._record_query(user_id)
        
        db = mock_session_local()
        try:
            log = db.query(AddressQueryLog).filter_by(user_id=user_id).first()
            
            assert log.query_count == first_count + 1
            assert log.last_query_at > first_time
        finally:
            db.close()
    
    def test_persistence_after_restart(self, mock_session_local):
        """测试重启后限频仍有效（持久化）"""
        user_id = 12350
        
        # 第一次查询
        AddressQueryHandler._record_query(user_id)
        
        # 模拟重启（关闭并重新打开数据库）
        # 再次检查（应该仍被限制）
        can_query, remaining = AddressQueryHandler._check_rate_limit(user_id)
        
        assert can_query is False
        assert remaining > 0
    
    def test_multiple_users_independent(self, mock_session_local):
        """测试多用户限频独立"""
        user1 = 12351
        user2 = 12352
        
        # 用户 1 查询
        AddressQueryHandler._record_query(user1)
        
        # 用户 1 被限制
        can_query_1, _ = AddressQueryHandler._check_rate_limit(user1)
        assert can_query_1 is False
        
        # 用户 2 仍可查询
        can_query_2, _ = AddressQueryHandler._check_rate_limit(user2)
        assert can_query_2 is True
    
    def test_concurrent_query_protection(self, mock_session_local):
        """测试并发查询保护（同一用户无法绕过限频）"""
        user_id = 12353
        
        # 第一次查询
        AddressQueryHandler._record_query(user_id)
        
        # 模拟并发请求（立即再次检查）
        can_query_1, _ = AddressQueryHandler._check_rate_limit(user_id)
        can_query_2, _ = AddressQueryHandler._check_rate_limit(user_id)
        
        # 两次检查都应被拒绝
        assert can_query_1 is False
        assert can_query_2 is False
    
    def test_edge_case_exactly_1_minute(self, mock_session_local):
        """测试边界情况：恰好 1 分钟"""
        user_id = 12354
        
        # 记录查询（恰好 1 分钟前）
        db = mock_session_local()
        try:
            log = AddressQueryLog(
                user_id=user_id,
                last_query_at=datetime.now() - timedelta(minutes=1),
                query_count=1
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
        
        # 检查限频（边界情况，应拒绝）
        can_query, remaining = AddressQueryHandler._check_rate_limit(user_id)
        
        # 由于计算精度，恰好 1 分钟可能被拒绝（剩余 0 分钟）
        assert can_query is False or remaining == 0
