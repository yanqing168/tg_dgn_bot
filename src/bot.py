#!/usr/bin/env python3
"""
Telegram Bot 主程序入口
"""
import asyncio
import logging
import re
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from src.config import settings
from src.database import init_db, init_db_safe, check_database_health
from src.menu.main_menu import MainMenuHandler
from .premium.handler_v2 import PremiumHandlerV2
from src.premium.delivery import PremiumDeliveryService
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
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram Bot 主类"""
    
    def __init__(self):
        """初始化 Bot"""
        self.app = None
        self.premium_handler = None
        self.wallet_manager = None
        self.scheduler = None
        
    async def initialize(self):
        """初始化 Bot 及其依赖"""
        logger.info("🚀 初始化 Bot...")
        
        # 安全初始化数据库
        try:
            init_db_safe()
            if not check_database_health():
                logger.warning("⚠️ 数据库健康检查未通过，但继续启动")
        except Exception as e:
            logger.error(f"数据库初始化警告: {e}")
            # 不阻止启动，尝试基础初始化
            init_db()
        
        # 连接 Redis
        await order_manager.connect()
        await suffix_manager.connect()
        logger.info("✅ Redis 连接成功")
        
        # 创建 Application
        self.app = Application.builder().token(settings.bot_token).build()
        
        # 初始化钱包管理器
        self.wallet_manager = WalletManager()
        logger.info("✅ 钱包管理器初始化完成")
        
        # 初始化 Premium 处理器 V2
        delivery_service = PremiumDeliveryService(
            bot=self.app.bot,
            order_manager=order_manager
        )
        
        # 获取bot用户名
        bot_info = await self.app.bot.get_me()
        bot_username = bot_info.username
        
        self.premium_handler = PremiumHandlerV2(
            order_manager=order_manager,
            suffix_manager=suffix_manager,
            delivery_service=delivery_service,
            receive_address=settings.usdt_trc20_receive_addr,
            bot_username=bot_username
        )
        
        logger.info("✅ 处理器初始化完成")

    async def _bootstrap_application(self):
        """初始化并启动应用公共部分"""
        await self.initialize()
        self.register_handlers()
        await self.app.initialize()
        await self.app.start()
        await self.setup_bot_commands()
        self.start_scheduler()

    def register_handlers(self):
        """注册所有命令和回调处理器"""
        logger.info("📝 注册处理器...")
        
        # === 第0组：全局导航处理器（最高优先级） ===
        from src.common.navigation_manager import NavigationManager
        self.app.add_handler(
            CallbackQueryHandler(
                NavigationManager.handle_navigation,
                pattern=r'^(back_to_main|nav_back_to_main)$'
            ),
            group=0
        )
        logger.info("✅ 全局导航处理器已注册（group=0）")
        
        # === 第1组：基础命令 ===
        self.app.add_handler(CommandHandler("start", MainMenuHandler.start_command), group=1)
        self.app.add_handler(CommandHandler("health", health_command), group=1)
        
        # === 第2组：功能模块（ConversationHandlers） ===
        # 增强帮助系统
        from src.help import get_help_handler
        self.app.add_handler(get_help_handler(), group=2)
        logger.info("✅ 帮助系统处理器已注册（分类帮助 + FAQ）")
        
        # 简单功能处理器
        from src.menu.simple_handlers import get_simple_handlers
        for handler in get_simple_handlers():
            self.app.add_handler(handler, group=2)
        logger.info("✅ 简单功能处理器已注册（联系客服、实时U价、免费克隆）")
        
        # Premium 会员直充
        self.app.add_handler(self.premium_handler.get_conversation_handler(), group=2)
        logger.info("✅ Premium V2 处理器已注册")
        
        # 个人中心
        from src.wallet.profile_handler import get_profile_handlers
        for handler in get_profile_handlers():
            self.app.add_handler(handler, group=2)
        
        # 个人中心主菜单入口
        self.app.add_handler(CallbackQueryHandler(
            ProfileHandler.profile_command_callback,
            pattern=r'^menu_profile$'
        ), group=2)
        logger.info("✅ 个人中心处理器已注册")
        
        # 地址查询
        self.app.add_handler(AddressQueryHandler.get_conversation_handler(), group=2)
        logger.info("✅ 地址查询处理器已注册")
        
        # 能量兑换（直转模式）
        self.app.add_handler(create_energy_direct_handler(), group=2)
        logger.info("✅ 能量兑换处理器已注册（TRX/USDT 直转模式）")
        
        # TRX 兑换
        trx_exchange_handler = TRXExchangeHandler()
        self.app.add_handler(trx_exchange_handler.get_handlers(), group=2)
        logger.info("✅ TRX 兑换处理器已注册")
        
        # === 第10组：管理员功能（较低优先级，避免截获公共回调） ===
        self.app.add_handler(admin_handler.get_conversation_handler(), group=10)
        logger.info("✅ 管理员面板处理器已注册（group=10）")
        
        self.app.add_handler(get_orders_handler(), group=10)
        logger.info("✅ 订单查询处理器已注册（管理员专用，group=10）")
        
        # === 第100组：备份处理器（兜底） ===
        self.app.add_handler(
            CallbackQueryHandler(
                NavigationManager.handle_fallback_callback,
                pattern=r'^.*$'
            ),
            group=100
        )
        logger.info("✅ 备份处理器已注册（group=100）")
        
        # === 注册完成 ===
        logger.info("✅ 所有处理器注册完成")
    
    async def start_polling(self):
        """启动 Bot (Polling 模式)"""
        logger.info("🤖 启动 Bot (Polling 模式)...")
        await self._bootstrap_application()
        await self.app.updater.start_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )
        
        logger.info("✅ Bot 启动成功！")
        logger.info(f"📱 Bot 用户名: @{(await self.app.bot.get_me()).username}")
        logger.info("🎯 等待用户消息...")
        
        # 保持运行
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("⏹️  收到停止信号...")
        finally:
            await self.stop()
    
    async def start_webhook(self):
        """启动 Bot (Webhook 模式)"""
        logger.info(
            "🤖 启动 Bot (Webhook 模式)... 监听 %s:%s",
            settings.bot_service_host,
            settings.bot_service_port,
        )
        if not settings.bot_webhook_url:
            raise ValueError("bot_webhook_url 未配置，无法启动 Webhook 模式")
        await self._bootstrap_application()
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
        logger.info(
            "✅ Webhook 启动成功：实例 %s → %s",
            settings.bot_instance_name,
            settings.bot_webhook_url,
        )
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("⏹️  收到停止信号...")
        finally:
            await self.stop()
    
    async def setup_bot_commands(self):
        """设置 Bot 菜单命令（左下角菜单按钮）"""
        from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
        
        # 1. 为所有用户设置通用命令（只显示 /start）
        common_commands = [
            BotCommand("start", "🏠 开始使用 / 主菜单"),
        ]
        await self.app.bot.set_my_commands(
            common_commands,
            scope=BotCommandScopeDefault()
        )
        logger.info("✅ 已设置通用用户命令")
        
        # 2. 为 Owner 设置管理员命令
        if settings.bot_owner_id and settings.bot_owner_id > 0:
            admin_commands = [
                BotCommand("start", "🏠 开始使用 / 主菜单"),
                BotCommand("health", "🏥 系统健康检查"),
                BotCommand("admin", "🔐 管理员面板"),
                BotCommand("orders", "📦 订单查询管理"),
            ]
            try:
                await self.app.bot.set_my_commands(
                    admin_commands,
                    scope=BotCommandScopeChat(chat_id=settings.bot_owner_id)
                )
                logger.info(f"✅ 已设置 Owner 管理员命令（User ID: {settings.bot_owner_id}）")
            except Exception as e:
                logger.warning(f"⚠️ 设置 Owner 命令失败: {e}")
        
        logger.info("✅ Bot 菜单命令已设置")
    
    def start_scheduler(self):
        """启动定时任务调度器"""
        try:
            self.scheduler = AsyncIOScheduler()
            
            # 添加订单超时检查任务（每5分钟执行一次）
            self.scheduler.add_job(
                order_expiry_task.run,
                trigger='interval',
                minutes=5,
                id='order_expiry_task',
                name='订单超时检查任务',
                replace_existing=True
            )
            
            # 添加 USDT 汇率刷新任务（每小时执行一次）
            job_queue = self.app.job_queue
            job_queue.run_repeating(refresh_usdt_rates_job, interval=3600, first=5, name="usdt_rates_refresh")

            # 启动调度器
            self.scheduler.start()
            logger.info("✅ 定时任务调度器已启动（每5分钟检查订单超时）")
            
        except Exception as e:
            logger.error(f"❌ 定时任务调度器启动失败: {e}", exc_info=True)
    
    async def stop(self):
        """停止 Bot"""
        logger.info("🛑 停止 Bot...")
        
        # 停止定时任务调度器
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            logger.info("✅ 定时任务调度器已停止")
        
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        
        # 断开 Redis
        await order_manager.disconnect()
        await suffix_manager.disconnect()
        
        logger.info("✅ Bot 已停止")


async def main():
    """主函数"""
    bot = TelegramBot()
    try:
        if settings.use_webhook:
            await bot.start_webhook()
        else:
            await bot.start_polling()
    except Exception as e:
        logger.error(f"❌ Bot 启动失败: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 再见！")
