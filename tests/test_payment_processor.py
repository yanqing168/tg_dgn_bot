"""
支付处理器测试
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json

from src.payments.order import OrderManager
from src.models import Order, OrderStatus, PaymentCallback
from src.payments.suffix_manager import suffix_manager


@pytest.fixture
def payment_processor():
    """创建支付处理器实例"""
    processor = OrderManager()
    
    # 模拟Redis客户端
    processor.redis_client = MagicMock()
    
    # 配置 Redis pipeline mock
    mock_pipeline = MagicMock()
    mock_pipeline.set = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=[True, True])
    processor.redis_client.pipeline.return_value = mock_pipeline
    
    # 配置其他 Redis 方法
    processor.redis_client.set = AsyncMock(return_value=True)
    processor.redis_client.get = AsyncMock(return_value=None)
    processor.redis_client.keys = AsyncMock(return_value=[])
    
    return processor


@pytest.fixture
def sample_order():
    """创建样例订单"""
    return Order(
        order_id="test_order_123",
        base_amount=10.0,
        unique_suffix=123,
        total_amount=10.123,
        user_id=12345,
        expires_at=datetime.now() + timedelta(minutes=30)
    )


@pytest.mark.asyncio
async def test_calculate_total_amount(payment_processor):
    """测试总金额计算"""
    from src.payments.amount_calculator import AmountCalculator
    
    base_amount = 10.0
    suffix = 123
    
    total = AmountCalculator.generate_payment_amount(base_amount, suffix)
    
    assert total == 10.123


def test_amounts_match(payment_processor):
    """测试金额匹配功能（避免浮点误差）"""
    from src.payments.amount_calculator import AmountCalculator
    
    # 精确匹配
    assert AmountCalculator.verify_amount(10.123, 10.123) is True
    
    # 浮点误差情况
    amount1 = 10.1 + 0.023  # 可能有浮点误差
    amount2 = 10.123
    assert AmountCalculator.verify_amount(amount1, amount2) is True
    
    # 不匹配
    assert AmountCalculator.verify_amount(10.123, 10.124) is False
    
    # 边界情况
    assert AmountCalculator.verify_amount(0.001, 0.001) is True
    assert AmountCalculator.verify_amount(999.999, 999.999) is True


@pytest.mark.asyncio
@patch('src.payments.order.suffix_manager')
async def test_create_order_success(mock_suffix_manager, payment_processor):
    """测试成功创建订单"""
    # 模拟后缀分配成功
    mock_suffix_manager.allocate_suffix = AsyncMock(return_value=123)
    mock_suffix_manager.release_suffix = AsyncMock(return_value=True)
    mock_suffix_manager._reserve_suffix = AsyncMock(return_value=True)
    
    order = await payment_processor.create_order(12345, 10.0)
    
    assert order is not None
    assert order.user_id == 12345
    assert order.base_amount == 10.0
    assert order.unique_suffix == 123
    assert order.total_amount == 10.123
    assert order.status == OrderStatus.PENDING


@pytest.mark.asyncio
@patch('src.payments.order.suffix_manager')
async def test_create_order_no_suffix_available(mock_suffix_manager, payment_processor):
    """测试没有可用后缀时创建订单失败"""
    # 模拟后缀分配失败
    mock_suffix_manager.allocate_suffix = AsyncMock(return_value=None)
    
    order = await payment_processor.create_order(12345, 10.0)
    
    assert order is None


@pytest.mark.asyncio
async def test_save_and_get_order(payment_processor, sample_order):
    """测试保存和获取订单"""
    # 模拟Redis操作
    order_data = sample_order.model_dump()
    order_data["created_at"] = sample_order.created_at.isoformat()
    order_data["updated_at"] = sample_order.updated_at.isoformat()
    order_data["expires_at"] = sample_order.expires_at.isoformat()
    
    payment_processor.redis_client.pipeline.return_value.execute.return_value = [True, True]
    payment_processor.redis_client.get.return_value = json.dumps(order_data)
    
    # 保存订单
    success = await payment_processor._save_order(sample_order)
    assert success is True
    
    # 获取订单
    retrieved_order = await payment_processor.get_order(sample_order.order_id)
    assert retrieved_order is not None
    assert retrieved_order.order_id == sample_order.order_id
    assert retrieved_order.total_amount == sample_order.total_amount


@pytest.mark.asyncio
async def test_find_order_by_amount(payment_processor, sample_order):
    """测试根据金额查找订单"""
    # 模拟Redis返回订单ID
    from src.payments.amount_calculator import AmountCalculator
    micro_amount = AmountCalculator.amount_to_micro_usdt(sample_order.total_amount)
    payment_processor.redis_client.get.return_value = sample_order.order_id
    
    # 模拟获取订单详情
    order_data = sample_order.model_dump()
    order_data["created_at"] = sample_order.created_at.isoformat()
    order_data["updated_at"] = sample_order.updated_at.isoformat()
    order_data["expires_at"] = sample_order.expires_at.isoformat()
    
    with patch.object(payment_processor, 'get_order', return_value=sample_order):
        found_order = await payment_processor.find_order_by_amount(sample_order.total_amount)
    
    assert found_order is not None
    assert found_order.order_id == sample_order.order_id


@pytest.mark.asyncio
@patch('src.payments.order.suffix_manager')
async def test_update_order_status(mock_suffix_manager, payment_processor, sample_order):
    """测试更新订单状态"""
    # 配置 async mock
    mock_suffix_manager.release_suffix = AsyncMock(return_value=True)
    
    # 模拟获取订单
    with patch.object(payment_processor, 'get_order', return_value=sample_order):
        with patch.object(payment_processor, '_save_order', return_value=True):
            success = await payment_processor.update_order_status(
                sample_order.order_id, 
                OrderStatus.PAID
            )
    
    assert success is True
    # 验证后缀被释放
    mock_suffix_manager.release_suffix.assert_called_once()


def test_valid_status_transitions(payment_processor):
    """测试状态转换验证"""
    # 有效转换
    assert payment_processor._is_valid_status_transition(
        OrderStatus.PENDING, OrderStatus.PAID
    ) is True
    
    assert payment_processor._is_valid_status_transition(
        OrderStatus.PENDING, OrderStatus.EXPIRED
    ) is True
    
    assert payment_processor._is_valid_status_transition(
        OrderStatus.PENDING, OrderStatus.CANCELLED
    ) is True
    
    # 无效转换
    assert payment_processor._is_valid_status_transition(
        OrderStatus.PAID, OrderStatus.PENDING
    ) is False
    
    assert payment_processor._is_valid_status_transition(
        OrderStatus.EXPIRED, OrderStatus.PAID
    ) is False


@pytest.mark.asyncio
async def test_get_order_statistics(payment_processor):
    """测试获取订单统计"""
    # 模拟Redis返回订单keys
    payment_processor.redis_client.keys.return_value = [
        "order:test_order_1",
        "order:test_order_2",
        "order:test_order_3"
    ]
    
    # 创建不同状态的订单
    orders = [
        Order(
            order_id="test_order_1",
            base_amount=10.0,
            unique_suffix=123,
            total_amount=10.123,
            user_id=12345,
            expires_at=datetime.now() + timedelta(minutes=30),
            status=OrderStatus.PENDING
        ),
        Order(
            order_id="test_order_2",
            base_amount=10.0,
            unique_suffix=124,
            total_amount=10.124,
            user_id=12346,
            expires_at=datetime.now() + timedelta(minutes=30),
            status=OrderStatus.PAID
        ),
        Order(
            order_id="test_order_3",
            base_amount=10.0,
            unique_suffix=125,
            total_amount=10.125,
            user_id=12347,
            expires_at=datetime.now() - timedelta(minutes=5),
            status=OrderStatus.EXPIRED
        )
    ]
    
    def mock_get_order(order_id):
        for order in orders:
            if order.order_id == order_id:
                return order
        return None
    
    with patch.object(payment_processor, 'get_order', side_effect=mock_get_order):
        with patch('src.payments.order.suffix_manager.cleanup_expired', return_value=2):
            stats = await payment_processor.get_order_statistics()
    
    assert stats["total_orders"] == 3
    assert stats["pending_orders"] == 1
    assert stats["paid_orders"] == 1
    assert stats["expired_orders"] == 1
    assert stats["cancelled_orders"] == 0
    assert stats["active_suffixes"] == 2