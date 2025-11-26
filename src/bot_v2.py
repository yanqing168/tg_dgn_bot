#!/usr/bin/env python3
"""
Telegram Bot 主程序入口 - 新架构版本
集成标准化模块和API接口
"""

import asyncio
import logging
import uvicorn
from typing import Optional
from telegram.ext import Application
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import settings
from src.database import init_db_safe, check_database_health
from src.core.registry import get_registry

# 导入标准化模块
from src.modules.premium.handler import PremiumModule
from src.modules.menu.handler import MainMenuModule
from src.modules.energy.handler import EnergyModule
from src.modules.address_query.handler import AddressQueryModule

# 导入旧模块（逐步迁移）
from src.wallet.profile_handler import ProfileHandler
from src.wallet.wallet_manager import WalletManager
from src.address_query.handler import AddressQueryHandler
from src.energy.handler_direct import create_energy_direct_handler
from src.trx_exchange.handler import TRXExchangeHandler
from src.payments.order import order_manager
from src.payments.suffix_manager import suffix_manager
from src.health import health_command
from src.bot_admin import admin_handler
from src.orders.query_handler import get_orders_handler
from src.tasks.order_expiry import order_expiry_task
from src.rates.jobs import refresh_usdt_rates_job

# 导入API
from src.api import create_api_app


# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBotV2:
    """Telegram Bot 主类 - 新架构版本"""
    
    def __init__(self):
        """初始化 Bot"""
        self.app: Optional[Application] = None
        self.api_app = None
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.registry = get_registry()
        self.wallet_manager = None
        
    async def initialize(self):
        """初始化 Bot 及其依赖"""
        logger.info("🚀 初始化 Bot V2...")
        
        # 1. 初始化数据库
        await self._init_database()
        
        # 2. 初始化Redis
        await self._init_redis()
        
        # 3. 创建Telegram Application（增加超时时间）
        from telegram.request import HTTPXRequest
        request = HTTPXRequest(
            connect_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=30.0
        )
        self.app = Application.builder().token(settings.bot_token).request(request).build()
        
        # 4. 初始化钱包管理器
        self.wallet_manager = WalletManager()
        logger.info("✅ 钱包管理器初始化完成")
        
        # 5. 注册标准化模块
        await self._register_standardized_modules()
        
        # 6. 注册旧模块（兼容性）
        await self._register_legacy_modules()
        
        # 7. 初始化API应用
        self.api_app = create_api_app()
        logger.info("✅ API应用初始化完成")
        
        logger.info("✅ Bot V2 初始化完成")
    
    async def _init_database(self):
        """初始化数据库"""
        try:
            init_db_safe()
            if not check_database_health():
                logger.warning("⚠️ 数据库健康检查未通过，但继续启动")
        except Exception as e:
            logger.error(f"数据库初始化警告: {e}")
    
    async def _init_redis(self):
        """初始化Redis连接"""
        await order_manager.connect()
        await suffix_manager.connect()
        logger.info("✅ Redis 连接成功")
    
    async def _register_standardized_modules(self):
        """注册标准化模块"""
        logger.info("📦 注册标准化模块...")
        
        # 注册主菜单模块（最高优先级）
        menu_module = MainMenuModule()
        self.registry.register(
            menu_module,
            priority=0,
            enabled=True,
            metadata={"description": "主菜单和导航"}
        )
        
        # 注册Premium模块
        from src.premium.delivery import PremiumDeliveryService
        
        delivery_service = PremiumDeliveryService(
            bot=self.app.bot,
            order_manager=order_manager
        )
        
        # 获取bot用户名（暂时使用默认值，稍后在初始化完成后更新）
        bot_username = getattr(settings, 'bot_username', 'bot')
        
        premium_module = PremiumModule(
            order_manager=order_manager,
            suffix_manager=suffix_manager,
            delivery_service=delivery_service,
            receive_address=settings.usdt_trc20_receive_addr,
            bot_username=bot_username
        )
        self.registry.register(
            premium_module,
            priority=2,
            enabled=True,
            metadata={"description": "Premium会员功能"}
        )
        
        # 注册能量模块 - 已修复，使用SafeConversationHandler
        energy_module = EnergyModule()
        self.registry.register(
            energy_module,
            priority=3,
            enabled=True,
            metadata={"description": "能量兑换功能"}
        )
        
        # 注册地址查询模块 - 已修复，使用SafeConversationHandler
        address_query_module = AddressQueryModule()
        self.registry.register(
            address_query_module,
            priority=4,
            enabled=True,
            metadata={"description": "地址查询功能"}
        )
        
        logger.info(f"✅ 注册了 {len(self.registry.list_modules())} 个标准化模块")
    
    async def _register_legacy_modules(self):
        """注册旧模块（向后兼容）"""
        logger.info("📦 注册兼容性模块...")
        
        # 健康检查（管理员命令）
        from telegram.ext import CommandHandler
        self.app.add_handler(CommandHandler("health", health_command), group=1)
        
        # 个人中心
        from telegram.ext import CallbackQueryHandler
        self.app.add_handler(
            CallbackQueryHandler(
                ProfileHandler.profile_command_callback,
                pattern=r'^menu_profile$'
            ), 
            group=2
        )
        
        # 地址查询 - 已迁移到标准化模块
        # self.app.add_handler(AddressQueryHandler.get_conversation_handler(), group=2)
        
        # 能量兑换 - 已迁移到标准化模块
        # self.app.add_handler(create_energy_direct_handler(), group=2)
        
        # TRX兑换
        trx_exchange_handler = TRXExchangeHandler()
        self.app.add_handler(trx_exchange_handler.get_handlers(), group=2)
        
        # 管理员功能
        self.app.add_handler(admin_handler.get_conversation_handler(), group=10)
        self.app.add_handler(get_orders_handler(), group=10)
        
        logger.info("✅ 兼容性模块注册完成")
    
    async def _bootstrap_application(self):
        """启动应用"""
        # 初始化所有标准化模块
        self.registry.initialize_all(self.app)
        
        # 设置Bot命令菜单
        await self._setup_bot_commands()
        
        # 初始化定时任务
        await self._init_scheduler()
    
    async def _setup_bot_commands(self):
        """设置Bot命令菜单"""
        try:
            from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
            
            # 通用命令
            common_commands = [
                BotCommand("start", "🏠 开始使用 / 主菜单"),
            ]
            await self.app.bot.set_my_commands(
                common_commands,
                scope=BotCommandScopeDefault()
            )
            logger.info("✅ 已设置Bot命令菜单")
        except Exception as e:
            logger.warning(f"设置Bot命令菜单失败（网络问题可忽略）: {e}")
        
        # 管理员命令
        if settings.bot_owner_id and settings.bot_owner_id > 0:
            try:
                admin_commands = common_commands + [
                    BotCommand("health", "🏥 健康检查"),
                    BotCommand("stats", "📊 统计信息"),
                    BotCommand("admin", "🔧 管理面板"),
                    BotCommand("orders", "📋 订单管理"),
                ]
                await self.app.bot.set_my_commands(
                    admin_commands,
                    scope=BotCommandScopeChat(chat_id=settings.bot_owner_id)
                )
                logger.info(f"✅ 已为管理员 {settings.bot_owner_id} 设置管理命令")
            except Exception as e:
                logger.warning(f"设置管理员命令失败（网络问题可忽略）: {e}")
    
    async def _init_scheduler(self):
        """初始化定时任务"""
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        
        # 订单过期检查（每分钟）
        self.scheduler.add_job(
            order_expiry_task.check_and_expire_orders,
            'interval',
            minutes=1,
            id='check_expired_orders',
            replace_existing=True
        )
        
        # USDT汇率刷新（每5分钟）
        # refresh_usdt_rates_job需要context参数，创建一个包装函数
        async def refresh_rates_wrapper():
            await refresh_usdt_rates_job(None)
        
        self.scheduler.add_job(
            refresh_rates_wrapper,
            'interval',
            minutes=5,
            id='refresh_usdt_rates',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("✅ 定时任务调度器已启动")
    
    async def start_with_api(self):
        """同时启动Bot和API服务"""
        logger.info("🚀 启动 Bot V2 with API...")
        
        await self.initialize()
        await self._bootstrap_application()
        
        # 启动API服务器
        api_config = uvicorn.Config(
            app=self.api_app,
            host=settings.api_host if hasattr(settings, 'api_host') else "0.0.0.0",
            port=settings.api_port if hasattr(settings, 'api_port') else 8001,
            log_level="info"
        )
        api_server = uvicorn.Server(api_config)
        
        # 创建任务并发运行Bot和API
        bot_task = asyncio.create_task(self._run_bot())
        api_task = asyncio.create_task(api_server.serve())
        
        # 获取并显示Bot信息
        try:
            bot_info = await self.app.bot.get_me()
            bot_username = bot_info.username
            logger.info(f"📱 Bot用户名: @{bot_username}")
            
            # 更新Premium模块的bot_username
            premium = self.registry.get_module("premium")
            if premium:
                premium.bot_username = bot_username
        except Exception as e:
            logger.warning(f"无法获取Bot信息: {e}")
        
        logger.info("✅ Bot V2 和 API 服务已启动")
        logger.info(f"🌐 API文档: http://localhost:{api_config.port}/api/docs")
        
        try:
            # 等待两个服务
            await asyncio.gather(bot_task, api_task)
        except KeyboardInterrupt:
            logger.info("⏹️ 收到停止信号...")
        finally:
            await self.stop()
    
    async def _run_bot(self):
        """运行Bot（Polling或Webhook）"""
        if settings.use_webhook:
            await self._start_webhook()
        else:
            await self._start_polling()
    
    async def _start_polling(self):
        """Polling模式"""
        # 初始化Application
        await self.app.initialize()
        
        # 启动轮询
        await self.app.start()
        await self.app.updater.start_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )
        
        # 等待停止信号
        await asyncio.Event().wait()
    
    async def _start_webhook(self):
        """Webhook模式"""
        # 初始化Application
        await self.app.initialize()
        await self.app.start()
        
        # 设置webhook
        await self.app.bot.set_webhook(
            settings.bot_webhook_url,
            drop_pending_updates=True,
            secret_token=settings.webhook_secret,
        )
        await self.app.updater.start_webhook(
            listen=settings.bot_service_host,
            port=settings.bot_service_port,
            webhook_url=settings.bot_webhook_url,
            secret_token=settings.webhook_secret,
            allowed_updates=["message", "callback_query"],
        )
        
        # 等待停止信号
        await asyncio.Event().wait()
    
    async def stop(self):
        """停止Bot"""
        logger.info("⏹️ 正在停止 Bot...")
        
        # 停止定时任务
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("✅ 定时任务调度器已停止")
        
        # 停止Telegram应用
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        
        # 断开Redis
        await order_manager.disconnect()
        await suffix_manager.disconnect()
        
        logger.info("✅ Bot V2 已停止")


async def main():
    """主函数"""
    bot = TelegramBotV2()
    try:
        await bot.start_with_api()
    except Exception as e:
        logger.error(f"❌ Bot V2 启动失败: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 再见！")
