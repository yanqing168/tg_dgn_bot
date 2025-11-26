"""
测试配置
"""
import pytest
import os
import sys
from unittest.mock import MagicMock, AsyncMock

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# 配置pytest异步测试
pytest_plugins = ['pytest_asyncio']

# 设置测试环境变量
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault('BOT_TOKEN', 'test_bot_token')
os.environ.setdefault('USDT_TRC20_RECEIVE_ADDR', 'TTestAddress123456789012345678901234')
os.environ.setdefault('WEBHOOK_SECRET', 'test_secret_key')
os.environ.setdefault('REDIS_HOST', 'localhost')
os.environ.setdefault('REDIS_PORT', '6379')
os.environ.setdefault('REDIS_DB', '0')  # 使用 DB 0（与 REDIS_URL 一致）
os.environ.setdefault('ORDER_TIMEOUT_MINUTES', '30')


@pytest.fixture
async def redis_client():
    """提供一个已连接的 Redis 客户端
    
    只有显式请求此固件的测试才会使用（通常是标记了 @pytest.mark.redis 的测试）
    """
    import redis.asyncio as redis
    import asyncio
    
    client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=3)
    
    # 等待 Redis 就绪（最多 10 秒）
    redis_available = False
    for _ in range(100):
        try:
            pong = await client.ping()
            if pong:
                redis_available = True
                break
        except Exception:
            await asyncio.sleep(0.1)
    
    if not redis_available:
        await client.aclose()
        pytest.skip("Redis not available, skipping Redis integration tests")
    
    yield client
    await client.aclose()


@pytest.fixture
async def clean_redis(redis_client):
    """清理 Redis 数据库（需要显式请求才会执行）
    
    在测试前后清理数据库，避免测试间污染
    """
    await redis_client.flushdb()
    yield
    await redis_client.flushdb()


@pytest.fixture
def test_db():
    """提供SQLite内存数据库用于测试"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.trx_exchange.models import Base as TRXBase
    from src.trx_exchange.rate_manager import Base as RateBase
    
    # 创建内存数据库
    engine = create_engine("sqlite:///:memory:")
    
    # 创建所有表
    TRXBase.metadata.create_all(engine)
    RateBase.metadata.create_all(engine)
    
    # 创建session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    # 清理
    session.close()
    engine.dispose()


def build_test_app_v2():
    """
    构建 V2 测试 Application（完全离线模式）
    
    参考 src/bot_v2.py 的逻辑，但不连接 Telegram API。
    
    Returns:
        Application: 配置好的测试 Application
    """
    from telegram.ext import Application
    
    # 创建 Application（使用假 token，不会连接网络）
    app = Application.builder().token("TEST:BOT_TOKEN_FOR_TESTING").build()
    
    # 设置 Application 为已初始化状态（绕过初始化检查）
    app._initialized = True
    
    # Mock 所有会触发网络请求的 bot 方法
    app.bot = MagicMock()
    app.bot.initialize = AsyncMock()
    app.bot.shutdown = AsyncMock()
    app.bot.get_me = AsyncMock(return_value=MagicMock(
        id=1234567890,
        username='test_bot',
        first_name='Test Bot',
        is_bot=True
    ))
    app.bot.set_my_commands = AsyncMock()
    app.bot.send_message = AsyncMock()
    app.bot.edit_message_text = AsyncMock()
    app.bot.answer_callback_query = AsyncMock()
    app.bot.send_photo = AsyncMock()
    app.bot.send_document = AsyncMock()
    app.bot.delete_message = AsyncMock()
    app.bot.copy_message = AsyncMock()
    app.bot.forward_message = AsyncMock()
    
    return app


def register_v2_modules(app):
    """
    向 Application 注册 V2 标准化模块
    
    Args:
        app: Application 实例
    """
    from src.core.registry import get_registry
    from src.modules.menu.handler import MainMenuModule
    from src.modules.premium.handler import PremiumModule
    from src.modules.energy.handler import EnergyModule
    from src.modules.address_query.handler import AddressQueryModule
    from src.payments.order import order_manager
    from src.payments.suffix_manager import suffix_manager
    from src.premium.delivery import PremiumDeliveryService
    
    registry = get_registry()
    
    # 注册主菜单模块
    menu_module = MainMenuModule()
    registry.register(
        menu_module,
        priority=0,
        enabled=True,
        metadata={"description": "主菜单和导航"}
    )
    
    # 注册 Premium 模块
    delivery_service = PremiumDeliveryService(
        bot=app.bot,
        order_manager=order_manager
    )
    premium_module = PremiumModule(
        order_manager=order_manager,
        suffix_manager=suffix_manager,
        delivery_service=delivery_service,
        receive_address="TTestAddress123456789012345678901234",
        bot_username="test_bot"
    )
    registry.register(
        premium_module,
        priority=2,
        enabled=True,
        metadata={"description": "Premium会员功能"}
    )
    
    # 注册能量模块
    energy_module = EnergyModule()
    registry.register(
        energy_module,
        priority=3,
        enabled=True,
        metadata={"description": "能量兑换功能"}
    )
    
    # 注册地址查询模块
    address_query_module = AddressQueryModule()
    registry.register(
        address_query_module,
        priority=4,
        enabled=True,
        metadata={"description": "地址查询功能"}
    )
    
    # 将所有注册的 handler 添加到 app
    for module_name in registry.list_modules():
        module = registry.get_module(module_name)
        if module and registry.is_enabled(module_name):
            handlers = module.get_handlers()
            for handler in handlers:
                app.add_handler(handler)
    
    return app


@pytest.fixture(autouse=True)
def isolate_database():
    """
    自动隔离数据库状态，防止测试间污染
    
    在每个测试前后保存和恢复 database 模块的全局状态
    """
    from src import database
    
    # 保存原始状态
    original_engine = getattr(database, 'engine', None)
    original_session_local = getattr(database, 'SessionLocal', None)
    
    yield
    
    # 恢复原始状态
    if original_engine is not None:
        database.engine = original_engine
    if original_session_local is not None:
        database.SessionLocal = original_session_local


@pytest.fixture
async def bot_app_v2():
    """
    V2 测试 Application fixture
    
    提供完全离线的 Application 实例，已注册所有 V2 标准化模块。
    所有 bot 方法都是 AsyncMock，不会触发网络请求。
    
    Yields:
        Application: 配置好的测试 Application
    """
    app = build_test_app_v2()
    
    # 注册 V2 模块
    register_v2_modules(app)
    
    yield app
    
    # 清理 registry（避免测试间污染）
    from src.core.registry import get_registry
    registry = get_registry()
    registry._modules.clear()
    registry._module_info.clear()
    registry._initialized = False