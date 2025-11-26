"""
Bot 管理员处理器

处理所有管理命令和回调查询。
"""
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters
)

from .middleware import owner_only, get_owner_id
from .menus import AdminMenus
from .config_manager import config_manager
from .audit_log import audit_logger
from .stats_manager import stats_manager
from src.common.settings_service import (
    get_address_cooldown_minutes,
    get_order_timeout_minutes,
    set_address_cooldown_minutes,
    set_order_timeout_minutes,
)

logger = logging.getLogger(__name__)

# 对话状态
(
    EDITING_PREMIUM_3, EDITING_PREMIUM_6, EDITING_PREMIUM_12,
    EDITING_TRX_RATE,
    EDITING_ENERGY_SMALL, EDITING_ENERGY_LARGE, EDITING_ENERGY_PACKAGE,
    EDITING_WELCOME, EDITING_CLONE, EDITING_SUPPORT,
    EDITING_TIMEOUT, EDITING_RATE_LIMIT
) = range(12)


class AdminHandler:
    """管理员处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.menus = AdminMenus()
    
    @owner_only
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /admin 命令"""
        user_id = update.effective_user.id
        
        # 记录审计日志
        audit_logger.log(
            admin_id=user_id,
            action="open_admin_panel",
            details="打开管理面板"
        )
        
        # 显示主菜单
        await update.message.reply_text(
            "🔐 <b>管理员面板</b>\n\n"
            "欢迎回来，管理员！\n"
            "请选择要执行的操作：",
            reply_markup=self.menus.main_menu(),
            parse_mode="HTML"
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理回调查询"""
        query = update.callback_query
        await query.answer()
        
        # 权限验证
        user_id = update.effective_user.id
        if user_id != get_owner_id():
            await query.edit_message_text("⛔ 权限不足")
            return
        
        data = query.data
        
        # 路由到不同的处理函数
        if data == "admin_main":
            await self._show_main_menu(query)
        elif data == "admin_stats":
            await self._show_stats(query, context)
        elif data == "admin_prices":
            await self._show_price_menu(query)
        elif data == "admin_content":
            await self._show_content_menu(query)
        elif data == "admin_settings":
            await self._show_settings_menu(query)
        elif data == "admin_exit":
            await query.edit_message_text("👋 已退出管理面板")
        
        # 价格配置
        elif data == "admin_price_premium":
            await self._show_premium_price(query)
        elif data == "admin_price_trx_rate":
            await self._show_trx_rate(query, context)
        elif data == "admin_price_energy":
            await self._show_energy_price(query)
        
        # Premium 价格编辑
        elif data.startswith("admin_premium_edit_"):
            months = data.split("_")[3]
            context.user_data['editing_premium_months'] = months
            await query.edit_message_text(
                f"💎 <b>修改 Premium {months}个月价格</b>\n\n"
                f"当前价格：${config_manager.get_price(f'premium_{months}_months', 0)} USDT\n\n"
                f"请输入新价格（仅数字，例如：15.5）：",
                parse_mode="HTML"
            )
            return EDITING_PREMIUM_3 if months == "3" else (
                EDITING_PREMIUM_6 if months == "6" else EDITING_PREMIUM_12
            )
        
        # TRX 汇率编辑
        elif data == "admin_edit_trx_rate":
            await query.edit_message_text(
                "🔄 <b>修改 TRX 兑换汇率</b>\n\n"
                f"当前汇率：1 USDT = {config_manager.get_price('trx_exchange_rate', 3.05)} TRX\n\n"
                "请输入新汇率（例如：3.15）：",
                parse_mode="HTML"
            )
            return EDITING_TRX_RATE
        
        # 能量价格编辑
        elif data.startswith("admin_energy_edit_"):
            energy_type = data.split("_")[3]
            context.user_data['editing_energy_type'] = energy_type
            
            type_map = {
                "small": ("小能量", "energy_small"),
                "large": ("大能量", "energy_large"),
                "package": ("笔数套餐", "energy_package_per_tx")
            }
            
            name, key = type_map[energy_type]
            current = config_manager.get_price(key, 0)
            
            await query.edit_message_text(
                f"⚡ <b>修改{name}价格</b>\n\n"
                f"当前价格：{current} TRX\n\n"
                f"请输入新价格（例如：3.5）：",
                parse_mode="HTML"
            )
            
            return EDITING_ENERGY_SMALL if energy_type == "small" else (
                EDITING_ENERGY_LARGE if energy_type == "large" else EDITING_ENERGY_PACKAGE
            )
        
        # 文案编辑
        elif data == "admin_content_welcome":
            await self._edit_welcome(query, context)
            return EDITING_WELCOME
        elif data == "admin_content_clone":
            await self._edit_clone(query, context)
            return EDITING_CLONE
        elif data == "admin_content_support":
            await self._edit_support(query, context)
            return EDITING_SUPPORT
        
        # 系统设置
        elif data == "admin_settings_timeout":
            await self._edit_timeout(query, context)
            return EDITING_TIMEOUT
        elif data == "admin_settings_rate_limit":
            await self._edit_rate_limit(query, context)
            return EDITING_RATE_LIMIT
        elif data == "admin_settings_clear_cache":
            await self._clear_cache(query)
        elif data == "admin_settings_status":
            await self._show_system_status(query)
    
    # ==================== 主菜单 ====================
    
    async def _show_main_menu(self, query):
        """显示主菜单"""
        await query.edit_message_text(
            "🔐 <b>管理员面板</b>\n\n"
            "请选择要执行的操作：",
            reply_markup=self.menus.main_menu(),
            parse_mode="HTML"
        )
    
    # ==================== 统计数据 ====================
    
    async def _show_stats(self, query, context):
        """显示统计数据"""
        order_stats = stats_manager.get_order_stats()
        user_stats = stats_manager.get_user_stats()
        revenue_stats = stats_manager.get_revenue_stats()
        
        text = (
            "📊 <b>统计数据</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>📦 订单统计</b>\n"
            f"• 总订单：{order_stats['total']}\n"
            f"• 待支付：{order_stats['pending']}\n"
            f"• 已支付：{order_stats['paid']}\n"
            f"• 已交付：{order_stats['delivered']}\n"
            f"• 已过期：{order_stats['expired']}\n"
            f"• 已取消：{order_stats['cancelled']}\n\n"
            "<b>👥 用户统计</b>\n"
            f"• 总用户：{user_stats['total']}\n"
            f"• 今日新增：{user_stats['today_new']}\n"
            f"• 本周新增：{user_stats['week_new']}\n\n"
            "<b>💰 收入统计 (USDT)</b>\n"
            f"• 总收入：${revenue_stats['total']}\n"
            f"• 今日：${revenue_stats['today']}\n"
            f"• 本周：${revenue_stats['week']}\n"
            f"• 本月：${revenue_stats['month']}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=self.menus.back_to_main(),
            parse_mode="HTML"
        )
        
        # 记录审计
        audit_logger.log(
            admin_id=query.from_user.id,
            action="view_stats",
            details="查看统计数据"
        )
    
    # ==================== 价格配置 ====================
    
    async def _show_price_menu(self, query):
        """显示价格配置菜单"""
        await query.edit_message_text(
            "💰 <b>价格配置</b>\n\n"
            "请选择要配置的项目：",
            reply_markup=self.menus.price_menu(),
            parse_mode="HTML"
        )
    
    async def _show_premium_price(self, query):
        """显示 Premium 价格"""
        price_3 = config_manager.get_price("premium_3_months", 10.0)
        price_6 = config_manager.get_price("premium_6_months", 18.0)
        price_12 = config_manager.get_price("premium_12_months", 30.0)
        
        text = (
            "💎 <b>Premium 会员价格</b>\n\n"
            f"• 3个月：${price_3} USDT\n"
            f"• 6个月：${price_6} USDT\n"
            f"• 12个月：${price_12} USDT\n\n"
            "点击下方按钮修改价格："
        )
        
        await query.edit_message_text(
            text,
            reply_markup=self.menus.premium_price_menu(),
            parse_mode="HTML"
        )
    
    async def _show_trx_rate(self, query, context):
        """显示 TRX 汇率"""
        rate = config_manager.get_price("trx_exchange_rate", 3.05)
        
        keyboard = [
            [InlineKeyboardButton("✏️ 修改汇率", callback_data="admin_edit_trx_rate")],
            [InlineKeyboardButton("🔙 返回", callback_data="admin_prices")]
        ]
        
        await query.edit_message_text(
            f"🔄 <b>TRX 兑换汇率</b>\n\n"
            f"当前汇率：1 USDT = {rate} TRX\n\n"
            f"示例：用户支付 10 USDT，将收到 {10 * rate} TRX",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    
    async def _show_energy_price(self, query):
        """显示能量价格"""
        small = config_manager.get_price("energy_small", 3.0)
        large = config_manager.get_price("energy_large", 6.0)
        package = config_manager.get_price("energy_package_per_tx", 3.6)
        
        text = (
            "⚡ <b>能量价格配置</b>\n\n"
            f"• 小能量 (6.5万)：{small} TRX\n"
            f"• 大能量 (13.1万)：{large} TRX\n"
            f"• 笔数套餐单价：{package} TRX/笔\n\n"
            "点击下方按钮修改价格："
        )
        
        await query.edit_message_text(
            text,
            reply_markup=self.menus.energy_price_menu(),
            parse_mode="HTML"
        )
    
    # ==================== 价格编辑处理 ====================
    
    async def handle_premium_price_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, months: str):
        """处理 Premium 价格输入"""
        try:
            new_price = float(update.message.text.strip())
            
            if new_price <= 0:
                await update.message.reply_text("❌ 价格必须大于 0，请重新输入：")
                return EDITING_PREMIUM_3 if months == "3" else (
                    EDITING_PREMIUM_6 if months == "6" else EDITING_PREMIUM_12
                )
            
            # 保存配置
            key = f"premium_{months}_months"
            success = config_manager.set_price(
                key, new_price, update.effective_user.id,
                f"Premium {months}个月价格"
            )
            
            if success:
                # 记录审计
                audit_logger.log(
                    admin_id=update.effective_user.id,
                    action="update_price",
                    target=key,
                    details=f"修改为 ${new_price}"
                )
                
                await update.message.reply_text(
                    f"✅ <b>价格已更新</b>\n\n"
                    f"Premium {months}个月：${new_price} USDT\n"
                    f"生效时间：立即\n\n"
                    f"使用 /admin 返回管理面板",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("❌ 保存失败，请稍后重试")
            
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text("❌ 格式错误，请输入数字（例如：15.5）：")
            return EDITING_PREMIUM_3 if months == "3" else (
                EDITING_PREMIUM_6 if months == "6" else EDITING_PREMIUM_12
            )
    
    async def handle_trx_rate_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 TRX 汇率输入"""
        try:
            new_rate = float(update.message.text.strip())
            
            if new_rate <= 0:
                await update.message.reply_text("❌ 汇率必须大于 0，请重新输入：")
                return EDITING_TRX_RATE
            
            # 保存配置
            success = config_manager.set_price(
                "trx_exchange_rate", new_rate, update.effective_user.id,
                "TRX 兑换汇率"
            )
            
            if success:
                # 记录审计
                audit_logger.log(
                    admin_id=update.effective_user.id,
                    action="update_trx_rate",
                    target="trx_exchange_rate",
                    details=f"修改为 {new_rate}"
                )
                
                await update.message.reply_text(
                    f"✅ <b>汇率已更新</b>\n\n"
                    f"新汇率：1 USDT = {new_rate} TRX\n"
                    f"生效时间：立即\n\n"
                    f"示例：用户支付 10 USDT = {10 * new_rate} TRX\n\n"
                    f"使用 /admin 返回管理面板",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("❌ 保存失败，请稍后重试")
            
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text("❌ 格式错误，请输入数字（例如：3.15）：")
            return EDITING_TRX_RATE
    
    async def handle_energy_price_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, energy_type: str):
        """处理能量价格输入"""
        try:
            new_price = float(update.message.text.strip())
            
            if new_price <= 0:
                await update.message.reply_text("❌ 价格必须大于 0，请重新输入：")
                return EDITING_ENERGY_SMALL if energy_type == "small" else (
                    EDITING_ENERGY_LARGE if energy_type == "large" else EDITING_ENERGY_PACKAGE
                )
            
            # 保存配置
            type_map = {
                "small": ("小能量", "energy_small"),
                "large": ("大能量", "energy_large"),
                "package": ("笔数套餐", "energy_package_per_tx")
            }
            
            name, key = type_map[energy_type]
            success = config_manager.set_price(
                key, new_price, update.effective_user.id,
                f"{name}价格(TRX)"
            )
            
            if success:
                # 记录审计
                audit_logger.log(
                    admin_id=update.effective_user.id,
                    action="update_energy_price",
                    target=key,
                    details=f"修改为 {new_price} TRX"
                )
                
                await update.message.reply_text(
                    f"✅ <b>{name}价格已更新</b>\n\n"
                    f"新价格：{new_price} TRX\n"
                    f"生效时间：立即\n\n"
                    f"使用 /admin 返回管理面板",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("❌ 保存失败，请稍后重试")
            
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text("❌ 格式错误，请输入数字（例如：3.5）：")
            return EDITING_ENERGY_SMALL if energy_type == "small" else (
                EDITING_ENERGY_LARGE if energy_type == "large" else EDITING_ENERGY_PACKAGE
            )
    
    async def handle_timeout_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理订单超时时间输入（管理员设置，不收费）"""
        try:
            new_timeout = int(update.message.text.strip())
            
            if not 5 <= new_timeout <= 120:
                await update.message.reply_text("❌ 超时时间需在 5~120 分钟之间，请重新输入：")
                return EDITING_TIMEOUT
            
            # 直接保存配置，不创建订单
            success = set_order_timeout_minutes(new_timeout, update.effective_user.id)
            
            if success:
                # 记录审计
                audit_logger.log(
                    admin_id=update.effective_user.id,
                    action="update_setting",
                    target="order_timeout_minutes",
                    details=f"修改为 {new_timeout} 分钟"
                )
                
                await update.message.reply_text(
                    f"✅ <b>订单超时时间已更新</b>\n\n"
                    f"新设置：{new_timeout} 分钟\n"
                    f"生效时间：立即\n\n"
                    f"使用 /admin 返回管理面板",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("❌ 保存失败，请稍后重试")
            
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text("❌ 格式错误，请输入整数（例如：45）：")
            return EDITING_TIMEOUT
    
    async def handle_rate_limit_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理地址查询限频时间输入（管理员设置，不收费）"""
        try:
            new_limit = int(update.message.text.strip())
            
            if not 1 <= new_limit <= 60:
                await update.message.reply_text("❌ 限频时间需在 1~60 分钟之间，请重新输入：")
                return EDITING_RATE_LIMIT
            
            # 直接保存配置，不创建订单
            success = set_address_cooldown_minutes(new_limit, update.effective_user.id)
            
            if success:
                # 记录审计
                audit_logger.log(
                    admin_id=update.effective_user.id,
                    action="update_setting",
                    target="address_query_rate_limit",
                    details=f"修改为 {new_limit} 分钟"
                )
                
                await update.message.reply_text(
                    f"✅ <b>地址查询限频已更新</b>\n\n"
                    f"新设置：{new_limit} 分钟\n"
                    f"生效时间：立即\n\n"
                    f"📝 说明：此功能为免费功能，用户每 {new_limit} 分钟可查询一次地址。\n\n"
                    f"使用 /admin 返回管理面板",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("❌ 保存失败，请稍后重试")
            
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text("❌ 格式错误，请输入整数（例如：60）：")
            return EDITING_RATE_LIMIT
    
    # ==================== 文案配置 ====================
    
    async def _show_content_menu(self, query):
        """显示文案配置菜单"""
        await query.edit_message_text(
            "📝 <b>文案配置</b>\n\n"
            "请选择要配置的项目：",
            reply_markup=self.menus.content_menu(),
            parse_mode="HTML"
        )
    
    async def _edit_welcome(self, query, context):
        """编辑欢迎语"""
        from src.config import settings
        current = settings.welcome_message
        
        await query.edit_message_text(
            "👋 <b>编辑欢迎语</b>\n\n"
            f"当前欢迎语：\n{current[:200]}...\n\n"
            "请发送新的欢迎语（支持HTML格式）：",
            parse_mode="HTML"
        )
    
    async def _edit_clone(self, query, context):
        """编辑免费克隆文案"""
        from src.config import settings
        current = settings.free_clone_message
        
        await query.edit_message_text(
            "🎁 <b>编辑免费克隆文案</b>\n\n"
            f"当前文案：\n{current[:200]}...\n\n"
            "请发送新的文案（支持HTML格式）：",
            parse_mode="HTML"
        )
    
    async def _edit_support(self, query, context):
        """编辑客服联系方式"""
        from src.config import settings
        current = settings.support_contact
        
        await query.edit_message_text(
            "👨‍💼 <b>编辑客服联系方式</b>\n\n"
            f"当前设置：{current}\n\n"
            "请发送新的客服 Telegram 账号（例如：@your_support）：",
            parse_mode="HTML"
        )
    
    # ==================== 系统设置 ====================
    
    async def _show_settings_menu(self, query):
        """显示系统设置菜单"""
        await query.edit_message_text(
            "⚙️ <b>系统设置</b>\n\n"
            "请选择要配置的项目：",
            reply_markup=self.menus.settings_menu(),
            parse_mode="HTML"
        )
    
    async def _edit_timeout(self, query, context):
        """编辑订单超时"""
        current = get_order_timeout_minutes()
        
        await query.edit_message_text(
            "⏰ <b>订单超时设置</b>\n\n"
            f"当前设置：{current} 分钟\n\n"
            "请输入新的超时时间（5-120 分钟，例如：45）：",
            parse_mode="HTML"
        )
    
    async def _edit_rate_limit(self, query, context):
        """编辑地址查询限频"""
        current = get_address_cooldown_minutes()
        
        await query.edit_message_text(
            "🔍 <b>地址查询限频</b>\n\n"
            f"当前设置：{current} 分钟\n\n"
            "请输入新的限频时间（1-60 分钟，例如：10）：",
            parse_mode="HTML"
        )
    
    async def _clear_cache(self, query):
        """清理Redis缓存"""
        try:
            import redis
            from src.config import settings
            
            r = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db
            )
            r.flushdb()
            
            audit_logger.log(
                admin_id=query.from_user.id,
                action="clear_cache",
                details="清理 Redis 缓存"
            )
            
            await query.edit_message_text(
                "✅ <b>缓存已清理</b>\n\n"
                "Redis 数据库已刷新。",
                reply_markup=self.menus.back_to_main(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            await query.edit_message_text(
                f"❌ 清理失败：{str(e)}",
                reply_markup=self.menus.back_to_main(),
                parse_mode="HTML"
            )
    
    async def _show_system_status(self, query):
        """显示系统状态"""
        try:
            import redis
            from src.config import settings
            
            # 检查 Redis
            r = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db
            )
            redis_ok = r.ping()
            
            # 检查数据库
            from sqlalchemy import create_engine, text
            engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./tg_bot.db"))
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
            
            text_msg = (
                "📊 <b>系统状态</b>\n\n"
                f"• Redis：{'✅ 正常' if redis_ok else '❌ 异常'}\n"
                f"• 数据库：{'✅ 正常' if db_ok else '❌ 异常'}\n"
                f"• Bot：✅ 运行中"
            )
            
            await query.edit_message_text(
                text_msg,
                reply_markup=self.menus.back_to_main(),
                parse_mode="HTML"
            )
            
        except Exception as e:
            logger.error(f"Failed to check system status: {e}")
            await query.edit_message_text(
                f"❌ 检查失败：{str(e)}",
                reply_markup=self.menus.back_to_main(),
                parse_mode="HTML"
            )
    
    # ==================== ConversationHandler ====================
    
    def get_conversation_handler(self) -> ConversationHandler:
        """获取对话处理器"""
        return ConversationHandler(
            entry_points=[
                CommandHandler("admin", self.admin_command),
                CallbackQueryHandler(
                    self.handle_callback,
                    pattern=r"^admin_"  # 所有admin回调都以admin_开头
                )
            ],
            states={
                EDITING_PREMIUM_3: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        lambda u, c: self.handle_premium_price_input(u, c, "3")
                    )
                ],
                EDITING_PREMIUM_6: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        lambda u, c: self.handle_premium_price_input(u, c, "6")
                    )
                ],
                EDITING_PREMIUM_12: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        lambda u, c: self.handle_premium_price_input(u, c, "12")
                    )
                ],
                EDITING_TRX_RATE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handle_trx_rate_input
                    )
                ],
                EDITING_ENERGY_SMALL: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        lambda u, c: self.handle_energy_price_input(u, c, "small")
                    )
                ],
                EDITING_ENERGY_LARGE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        lambda u, c: self.handle_energy_price_input(u, c, "large")
                    )
                ],
                EDITING_ENERGY_PACKAGE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        lambda u, c: self.handle_energy_price_input(u, c, "package")
                    )
                ],
                EDITING_TIMEOUT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handle_timeout_input
                    )
                ],
                EDITING_RATE_LIMIT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handle_rate_limit_input
                    )
                ],
            },
            fallbacks=[
                CommandHandler("cancel", lambda u, c: ConversationHandler.END)
            ],
            allow_reentry=True,
            per_chat=True,
            per_user=True,
            per_message=False,
        )


# 全局处理器实例
admin_handler = AdminHandler()
