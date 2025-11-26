"""
主菜单处理器
"""
import logging
import json
from datetime import datetime
from typing import Optional
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import ContextTypes
from src.utils.content_helper import get_content
from ..rates.service import get_or_refresh_rates

logger = logging.getLogger(__name__)


class MainMenuHandler:
    MAX_MERCHANT_ROWS = 10
    CHANNEL_TITLES = {
        "all": "✅ 全部渠道报价",
        "bank": "🏦 银行卡渠道",
        "alipay": "💴 支付宝渠道",
        "wechat": "🟢 微信渠道",
    }
    CHANNEL_ICONS = {
        "bank": "🏦",
        "alipay": "💴",
        "wechat": "🟢",
    }
    """主菜单处理器"""

    @staticmethod
    def _build_promotion_buttons():
        """构建引流按钮（从配置读取）"""
        from ..config import settings
        
        try:
            # 解析配置的按钮
            buttons_config = settings.promotion_buttons
            # 移除换行和多余空格
            buttons_config = buttons_config.replace('\n', '').replace(' ', '')
            # 解析为列表（安全地使用 JSON）
            button_rows = json.loads(f'[{buttons_config}]')
            
            keyboard = []
            for row in button_rows:
                button_row = []
                for btn in row:
                    text = btn.get('text', '')
                    url = btn.get('url')
                    callback = btn.get('callback')
                    
                    if url:
                        # 外部链接按钮
                        button_row.append(InlineKeyboardButton(text, url=url))
                    elif callback:
                        # 回调按钮
                        button_row.append(InlineKeyboardButton(text, callback_data=callback))
                
                if button_row:
                    keyboard.append(button_row)
            
            return keyboard
        except Exception as e:
            logger.error(f"解析引流按钮配置失败: {e}")
            # 返回默认按钮
            return [
                [
                    InlineKeyboardButton("💎 Premium直充", callback_data="menu_premium"),
                    InlineKeyboardButton("🏠 个人中心", callback_data="menu_profile")
                ],
                [
                    InlineKeyboardButton("🔍 地址查询", callback_data="menu_address_query"),
                    InlineKeyboardButton("⚡ 能量兑换", callback_data="menu_energy")
                ],
                [
                    InlineKeyboardButton("🎁 免费克隆", callback_data="menu_clone"),
                    InlineKeyboardButton("👨‍💼 联系客服", callback_data="menu_support")
                ]
            ]
    
    @staticmethod
    def _build_reply_keyboard() -> ReplyKeyboardMarkup:
        reply_keyboard = [
            [KeyboardButton("💎 Premium会员"), KeyboardButton("⚡ 能量兑换")],
            [KeyboardButton("🔍 地址查询"), KeyboardButton("👤 个人中心")],
            [KeyboardButton("🔄 TRX 兑换"), KeyboardButton("👨‍💼 联系客服")],
            [KeyboardButton("💵 实时U价"), KeyboardButton("🎁 免费克隆")],
        ]
        return ReplyKeyboardMarkup(
            reply_keyboard,
            resize_keyboard=True,
            one_time_keyboard=False,
        )

    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        from ..config import settings
        
        user = update.effective_user
        
        # 重置键盘显示标志
        context.user_data['main_menu_keyboard_shown'] = False
        
        # 从数据库读取欢迎语（支持热更新）
        text = get_content("welcome_message", default=settings.welcome_message)
        text = text.replace("{first_name}", user.first_name)
        
        # 构建引流按钮（InlineKeyboard）
        inline_keyboard = MainMenuHandler._build_promotion_buttons()
        inline_markup = InlineKeyboardMarkup(inline_keyboard)
        
        # 构建底部键盘（ReplyKeyboard）- 8个按钮，4x2布局
        reply_markup = MainMenuHandler._build_reply_keyboard()
        
        # 先发送带 InlineKeyboard 的消息
        await update.message.reply_text(
            text, 
            parse_mode="HTML", 
            reply_markup=inline_markup
        )
        
        # 再设置底部键盘
        await update.message.reply_text(
            "📱 使用下方按钮快速访问功能：",
            reply_markup=reply_markup
        )
        context.user_data['main_menu_keyboard_shown'] = True
    
    @staticmethod
    async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示主菜单（回调）"""
        from ..config import settings
        
        # 任何返回主菜单的场景都视为输入流程结束，清理地址查询等待状态
        context.user_data.pop("awaiting_address", None)

        reply_keyboard_markup = MainMenuHandler._build_reply_keyboard()
        keyboard = MainMenuHandler._build_promotion_buttons()
        inline_reply_markup = InlineKeyboardMarkup(keyboard)

        # 使用配置的欢迎语（简化版）
        text = (
            "🤖 <b>主菜单</b>\n\n"
            "📋 请选择功能："
        )

        query = update.callback_query
        if query:
            await query.answer()
            try:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=inline_reply_markup)
            except Exception:
                await query.message.reply_text(text, parse_mode="HTML", reply_markup=inline_reply_markup)
            
            # 检查是否已经设置了ReplyKeyboard
            # 避免重复发送键盘提示消息
            if not context.user_data.get('main_menu_keyboard_shown'):
                await query.message.reply_text(
                    "📱 使用下方按钮快速访问功能：",
                    reply_markup=reply_keyboard_markup,
                )
                context.user_data['main_menu_keyboard_shown'] = True
        else:
            message = update.message or update.effective_message
            if not message:
                return

            await message.reply_text(text, parse_mode="HTML", reply_markup=inline_reply_markup)
            # 只在新对话开始时显示键盘
            if not context.user_data.get('main_menu_keyboard_shown'):
                await message.reply_text(
                    "📱 使用下方按钮快速访问功能：",
                    reply_markup=reply_keyboard_markup,
                )
                context.user_data['main_menu_keyboard_shown'] = True
    
    @staticmethod
    async def handle_free_clone(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理免费克隆功能"""
        from ..config import settings
        
        query = update.callback_query
        await query.answer()
        
        # 从数据库读取免费克隆文案（支持热更新）
        text = get_content("free_clone_message", default=settings.free_clone_message)
        
        keyboard = [
            [InlineKeyboardButton("👨‍💼 联系客服", callback_data="menu_support")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理联系客服"""
        from ..config import settings
        
        query = update.callback_query
        if query:
            await query.answer()
        
        # 从数据库读取客服联系方式（支持热更新）
        support_contact = get_content("support_contact", default=settings.support_contact)
        
        text = (
            "👨‍💼 <b>联系客服</b>\n\n"
            f"客服 Telegram: {support_contact}\n\n"
            "工作时间: 24/7 全天候服务"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /help 命令"""
        # 从数据库读取帮助文案（支持热更新）
        default_help = (
            "📚 <b>帮助文档</b>\n\n"
            "<b>🎯 可用命令：</b>\n"
            "/start - 显示主菜单\n"
            "/help - 显示帮助信息\n"
            "/premium - 购买 Premium 会员\n"
            "/profile - 个人中心\n"
            "/cancel - 取消当前操作\n\n"
            "<b>💡 使用说明：</b>\n"
            "1. 点击主菜单按钮选择功能\n"
            "2. 按照提示完成操作\n"
            "3. 遇到问题可随时联系客服\n\n"
            "<b>💰 支付说明：</b>\n"
            "• 支持 TRC20 USDT 支付\n"
            "• 支付后 2-5 分钟自动到账\n"
            "• 请确保转账金额精确到小数点后3位\n\n"
            "如需更多帮助，请联系客服 👨‍💼"
        )
        text = get_content("help_message", default=default_help)
        
        keyboard = [[InlineKeyboardButton("🏠 返回主菜单", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    def _format_updated_time(updated_at: str) -> str:
        try:
            dt = datetime.fromisoformat(updated_at)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return updated_at

    @staticmethod
    def _build_channel_block(channel_key: str, title: str, rates: dict) -> str:
        details = rates.get("details", {}).get(channel_key, {})
        merchants = details.get("merchants", [])
        lines = []

        if merchants:
            for merchant in merchants[: MainMenuHandler.MAX_MERCHANT_ROWS]:
                price = merchant.get("price")
                name = merchant.get("name", "商家")
                try:
                    price_text = f"{float(price):.4f}"
                except (TypeError, ValueError):
                    price_text = "-"
                lines.append(f"💎 <b>{price_text}</b> {name}")
        else:
            fallback_price = rates.get(channel_key) or rates.get("base")
            if fallback_price:
                lines.append(f"💰 当前最低价：<b>{float(fallback_price):.4f} CNY</b>")
            lines.append("ℹ️ 暂无更多挂单信息")

        body = "\n".join(lines)
        return f"{title}\n{body}"

    @staticmethod
    def _build_all_block(rates: dict) -> str:
        aggregated = []
        details = rates.get("details", {})
        for key in ("bank", "alipay", "wechat"):
            icon = MainMenuHandler.CHANNEL_ICONS.get(key, "💎")
            merchants = details.get(key, {}).get("merchants", [])
            for merchant in merchants:
                aggregated.append({
                    "channel": key,
                    "icon": icon,
                    "price": merchant.get("price"),
                    "name": merchant.get("name", "商家"),
                })

        if not aggregated:
            fallback = rates.get("base")
            if fallback:
                return (
                    "✅ 全部渠道报价\n"
                    f"💎 <b>{float(fallback):.4f}</b> 当前最低价\n"
                    "ℹ️ 暂无挂单详情"
                )
            return "✅ 全部渠道报价\nℹ️ 暂无可用报价"

        filtered = sorted(
            aggregated,
            key=lambda item: item.get("price") if item.get("price") is not None else float("inf")
        )[: MainMenuHandler.MAX_MERCHANT_ROWS]

        lines = []
        for entry in filtered:
            price = entry.get("price")
            try:
                price_text = f"{float(price):.4f}"
            except (TypeError, ValueError):
                price_text = "-"
            lines.append(f"{entry['icon']} <b>{price_text}</b> {entry['name']}")

        return f"{MainMenuHandler.CHANNEL_TITLES['all']}\n" + "\n".join(lines)

    @staticmethod
    def _build_rates_text(channel: str, rates: dict) -> str:
        updated_at = rates.get("updated_at", "-")
        formatted_time = MainMenuHandler._format_updated_time(updated_at)
        sections = []

        if channel == "all":
            sections.append(MainMenuHandler._build_all_block(rates))
        else:
            sections.append(MainMenuHandler._build_channel_block(channel, MainMenuHandler.CHANNEL_TITLES[channel], rates))

        body = "\n\n".join(sections)
        return (
            "📊 实时U价看板\n\n"
            f"🕒 更新：{formatted_time}\n\n"
            f"{body}\n\n"
            "点击下方按钮切换渠道或返回主菜单。"
        )

    @staticmethod
    def _build_rates_keyboard() -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("✅ 全部", callback_data="menu_rates_all"),
                InlineKeyboardButton("🏦 银行卡", callback_data="menu_rates_bank"),
            ],
            [
                InlineKeyboardButton("💴 支付宝", callback_data="menu_rates_alipay"),
                InlineKeyboardButton("🟢 微信", callback_data="menu_rates_wechat"),
            ],
            [InlineKeyboardButton("❌ 取消", callback_data="back_to_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    async def show_usdt_rates(update: Update, context: ContextTypes.DEFAULT_TYPE, channel: str = "all"):
        rates = await get_or_refresh_rates()
        keyboard = MainMenuHandler._build_rates_keyboard()

        if rates:
            text = MainMenuHandler._build_rates_text(channel, rates)
        else:
            text = (
                "📊 实时U价看板\n\n"
                "⚠️ 暂未获取到汇率缓存，已尝试实时刷新失败。\n"
                "请稍后重试或联系客服。"
            )

        query = update.callback_query if update.callback_query else None

        if query:
            await query.answer()
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")

    @staticmethod
    async def show_usdt_rates_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await MainMenuHandler.show_usdt_rates(update, context, "all")

    @staticmethod
    async def show_usdt_rates_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await MainMenuHandler.show_usdt_rates(update, context, "bank")

    @staticmethod
    async def show_usdt_rates_alipay(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await MainMenuHandler.show_usdt_rates(update, context, "alipay")

    @staticmethod
    async def show_usdt_rates_wechat(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await MainMenuHandler.show_usdt_rates(update, context, "wechat")
    @staticmethod
    async def handle_keyboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理底部键盘按钮"""
        text = update.message.text
        
        # 清除地址查询等待状态，避免误触发
        context.user_data.pop('awaiting_address', None)
        
        # 根据按钮文字路由到对应功能
        # 注意：Premium、能量兑换、TRX 兑换已由各自的 ConversationHandler 处理
        # 这些按钮不在 keyboard_buttons 列表中，不会触发此 handler
        
        if text == "🔍 地址查询":
            # 导航到地址查询
            from ..address_query.handler import AddressQueryHandler
            await AddressQueryHandler.query_address(update, context)
        
        elif text == "👤 个人中心":
            # 导航到个人中心
            from ..wallet.profile_handler import ProfileHandler
            await ProfileHandler.profile_command(update, context)
        
        elif text == "👨‍💼 联系客服":
            # 显示客服联系方式（从数据库读取）
            from ..config import settings
            support_contact = get_content("support_contact", default=settings.support_contact)
            await update.message.reply_text(
                f"👨‍💼 <b>联系客服</b>\n\n{support_contact}",
                parse_mode="HTML"
            )
        
        elif text == "💵 实时U价":
            # 显示实时 USDT 汇率
            await MainMenuHandler.show_usdt_rates_all(update, context)
        
        elif text == "🎁 免费克隆":
            # 免费克隆功能（从数据库读取文案）
            from ..config import settings
            clone_message = get_content("free_clone_message", default=settings.free_clone_message)
            keyboard = [[InlineKeyboardButton("👨‍💼 联系客服", callback_data="menu_support")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                clone_message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
