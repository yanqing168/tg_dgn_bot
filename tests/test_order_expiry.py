"""
测试订单超时自动处理任务
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.tasks.order_expiry import OrderExpiryTask
from src.database import Order
from src.config import settings


class TestOrderExpiryTask:
    """测试订单超时处理任务"""

    @pytest.fixture
    def task(self):
        """创建任务实例"""
        return OrderExpiryTask()

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = MagicMock()
        return session

    def test_init(self, task):
        """测试初始化"""
        assert task is not None
        assert task.suffix_manager is not None

    def test_should_release_suffix(self, task):
        """测试判断是否需要释放后缀"""
        # 需要释放后缀的订单类型
        assert task._should_release_suffix("premium") is True
        assert task._should_release_suffix("deposit") is True
        assert task._should_release_suffix("trx_exchange") is True
        
        # 不需要释放后缀的订单类型
        assert task._should_release_suffix("energy") is False
        assert task._should_release_suffix("unknown") is False

    def test_extract_suffix_from_amount(self, task):
        """测试从金额中提取后缀"""
        # 正常情况
        assert task._extract_suffix_from_amount(10_123_000) == 123  # 10.123 USDT
        assert task._extract_suffix_from_amount(18_456_000) == 456  # 18.456 USDT
        assert task._extract_suffix_from_amount(30_789_000) == 789  # 30.789 USDT
        
        # 边界值
        assert task._extract_suffix_from_amount(5_001_000) == 1    # 5.001 USDT
        assert task._extract_suffix_from_amount(5_999_000) == 999  # 5.999 USDT
        
        # 整数金额（后缀为0，应返回None）
        assert task._extract_suffix_from_amount(10_000_000) is None  # 10.000 USDT

    def test_extract_suffix_rounding(self, task):
        """测试后缀提取的四舍五入"""
        # 测试浮点数精度问题
        # 10.1234999... USDT 应该提取为 123（四舍五入）
        amount = int(10.1234999 * 1_000_000)
        result = task._extract_suffix_from_amount(amount)
        assert result in [123, 124]  # 允许误差

    @patch('src.tasks.order_expiry.SessionLocal')
    def test_check_and_expire_orders_no_orders(self, mock_session_local, task):
        """测试没有过期订单的情况"""
        # 模拟数据库查询返回空列表
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        
        stats = task.check_and_expire_orders()
        
        assert stats["checked"] == 0
        assert stats["expired"] == 0
        assert stats["suffix_released"] == 0
        assert stats["errors"] == 0

    @patch('src.tasks.order_expiry.SessionLocal')
    def test_check_and_expire_orders_with_premium_order(self, mock_session_local, task):
        """测试处理 Premium 过期订单"""
        # 创建模拟的过期订单
        expired_order = Mock(spec=Order)
        expired_order.order_id = "PREM_TEST_001"
        expired_order.order_type = "premium"
        expired_order.status = "PENDING"
        expired_order.amount_usdt = 10_123_000  # 10.123 USDT
        expired_order.created_at = datetime.now() - timedelta(hours=1)
        
        # 模拟数据库
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_session.execute.return_value.scalars.return_value.all.return_value = [expired_order]
        
        # 模拟后缀释放
        with patch.object(task.suffix_manager, 'release_suffix', return_value=True):
            stats = task.check_and_expire_orders()
        
        assert stats["checked"] == 1
        assert stats["expired"] == 1
        assert stats["suffix_released"] == 1
        assert stats["errors"] == 0
        
        # 验证订单状态已更新
        assert expired_order.status == "EXPIRED"

    @patch('src.tasks.order_expiry.SessionLocal')
    def test_check_and_expire_orders_with_energy_order(self, mock_session_local, task):
        """测试处理能量订单（不需要释放后缀）"""
        # 创建模拟的能量订单
        expired_order = Mock(spec=Order)
        expired_order.order_id = "ENERGY_TEST_001"
        expired_order.order_type = "energy"
        expired_order.status = "PENDING"
        expired_order.amount_usdt = 3_000_000  # 3 USDT
        expired_order.created_at = datetime.now() - timedelta(hours=1)
        
        # 模拟数据库
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_session.execute.return_value.scalars.return_value.all.return_value = [expired_order]
        
        stats = task.check_and_expire_orders()
        
        assert stats["checked"] == 1
        assert stats["expired"] == 1
        assert stats["suffix_released"] == 0  # 能量订单不释放后缀
        assert stats["errors"] == 0

    @patch('src.tasks.order_expiry.SessionLocal')
    def test_check_and_expire_orders_with_multiple_orders(self, mock_session_local, task):
        """测试处理多个过期订单"""
        # 创建多个过期订单
        orders = []
        for i in range(3):
            order = Mock(spec=Order)
            order.order_id = f"PREM_TEST_{i:03d}"
            order.order_type = "premium"
            order.status = "PENDING"
            order.amount_usdt = 10_000_000 + (i + 1) * 1000  # 10.001, 10.002, 10.003
            order.created_at = datetime.now() - timedelta(hours=1)
            orders.append(order)
        
        # 模拟数据库
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_session.execute.return_value.scalars.return_value.all.return_value = orders
        
        # 模拟后缀释放
        with patch.object(task.suffix_manager, 'release_suffix', return_value=True):
            stats = task.check_and_expire_orders()
        
        assert stats["checked"] == 3
        assert stats["expired"] == 3
        assert stats["suffix_released"] == 3
        assert stats["errors"] == 0

    @patch('src.tasks.order_expiry.SessionLocal')
    def test_check_and_expire_orders_with_error(self, mock_session_local, task):
        """测试处理订单时发生错误"""
        # 创建会引发错误的订单
        error_order = Mock(spec=Order)
        error_order.order_id = "ERROR_TEST_001"
        error_order.order_type = "premium"
        error_order.status = "PENDING"
        error_order.amount_usdt = 10_123_000
        error_order.created_at = datetime.now() - timedelta(hours=1)
        
        # 模拟数据库
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_session.execute.return_value.scalars.return_value.all.return_value = [error_order]
        
        # 模拟后缀释放失败
        with patch.object(task.suffix_manager, 'release_suffix', side_effect=Exception("Redis error")):
            stats = task.check_and_expire_orders()
        
        # 订单仍然应该被标记为过期（即使后缀释放失败）
        assert stats["checked"] == 1
        assert stats["expired"] == 1
        # 错误应该被捕获但不阻止流程
        assert error_order.status == "EXPIRED"

    @patch('src.tasks.order_expiry.SessionLocal')
    def test_check_and_expire_orders_suffix_release_failure(self, mock_session_local, task):
        """测试后缀释放失败的情况"""
        expired_order = Mock(spec=Order)
        expired_order.order_id = "PREM_TEST_001"
        expired_order.order_type = "premium"
        expired_order.status = "PENDING"
        expired_order.amount_usdt = 10_123_000
        expired_order.created_at = datetime.now() - timedelta(hours=1)
        
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_session.execute.return_value.scalars.return_value.all.return_value = [expired_order]
        
        # 模拟后缀管理器抛出异常（释放失败）
        with patch.object(task.suffix_manager, 'release_suffix', side_effect=Exception("Redis connection error")):
            stats = task.check_and_expire_orders()
        
        # 注意：在当前实现中，即使后缀释放失败，订单仍然会被标记为过期
        # 并且会继续计数（因为代码没有在异常时停止计数）
        assert stats["checked"] == 1
        assert stats["expired"] == 1
        # 由于后缀释放抛出异常，不会增加 suffix_released 计数
        # 但错误会被捕获，所以流程继续

    def test_run(self, task):
        """测试 run 方法（由调度器调用）"""
        with patch.object(task, 'check_and_expire_orders', return_value={"checked": 0, "expired": 0}):
            result = task.run()
            assert "checked" in result
            assert "expired" in result


@pytest.mark.integration
class TestOrderExpiryIntegration:
    """订单超时处理集成测试（需要数据库）"""

    @pytest.fixture
    def test_db(self):
        """使用独立内存数据库测试"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.database import Base, Order
        
        # 创建完全隔离的内存数据库
        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=test_engine)
        TestSession = sessionmaker(bind=test_engine)
        
        yield TestSession
        
        test_engine.dispose()

    def test_full_expiry_flow(self, test_db):
        """测试完整的订单过期流程（集成测试）"""
        from src.database import Order
        from src.tasks.order_expiry import OrderExpiryTask
        
        # 使用测试 session
        TestSessionLocal = test_db
        
        # 创建测试订单
        session = TestSessionLocal()
        try:
            # 创建一个过期的订单
            expired_order = Order(
                order_id="PREM_INTEGRATION_001",
                order_type="premium",
                user_id=123456789,
                base_amount=10_000_000,  # 10 USDT
                unique_suffix=123,
                amount_usdt=10_123_000,  # 10.123 USDT
                status="PENDING",
                created_at=datetime.now() - timedelta(hours=1),
                expires_at=datetime.now() + timedelta(minutes=30)  # 30分钟后过期
            )
            session.add(expired_order)
            
            # 创建一个未过期的订单
            valid_order = Order(
                order_id="PREM_INTEGRATION_002",
                order_type="premium",
                user_id=123456789,
                base_amount=10_000_000,  # 10 USDT
                unique_suffix=456,
                amount_usdt=10_456_000,  # 10.456 USDT
                status="PENDING",
                created_at=datetime.now() - timedelta(minutes=5),
                expires_at=datetime.now() + timedelta(minutes=30)  # 30分钟后过期
            )
            session.add(valid_order)
            
            session.commit()
            
            # 执行超时检查任务，使用测试数据库
            with patch('src.tasks.order_expiry.SessionLocal', TestSessionLocal):
                task = OrderExpiryTask()
                with patch.object(task.suffix_manager, 'release_suffix', return_value=True):
                    stats = task.check_and_expire_orders()
            
            # 验证结果
            assert stats["checked"] == 1  # 只有1个过期
            assert stats["expired"] == 1
            
            # 重新查询订单（避免 SQLAlchemy 对象比较问题）
            session.expire_all()
            expired_order = session.query(Order).filter_by(order_id="PREM_INTEGRATION_001").first()
            valid_order = session.query(Order).filter_by(order_id="PREM_INTEGRATION_002").first()
            
            # 验证订单状态
            assert expired_order.status == "EXPIRED"
            assert valid_order.status == "PENDING"  # 未过期的订单应保持原状
            
        finally:
            session.close()
