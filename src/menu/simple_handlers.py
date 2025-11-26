"""
简单功能处理器
处理不需要对话流程的功能按钮
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters

from src.common.decorators import error_handler, log_action
from src.utils.content_helper import get_content
from src.config import settings

logger = logging.getLogger(__name__)


class SimpleHandlers:
    """简单功能处理器集合"""
    
    @staticmethod
    @error_handler
    @log_action("联系客服")
    async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理联系客服按钮"""
        # 支持Reply按钮和Inline按钮两种入口
        if update.callback_query:
            await update.callback_query.answer()
            
        # 从数据库读取客服联系方式
        support_contact = get_content("support_contact", default=settings.support_contact)
        
        text = f"👨‍💼 <b>联系客服</b>\n\n{support_contact}"
        
        # 添加返回按钮
        keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        
        logger.info(f"用户 {update.effective_user.id} 查看了客服联系方式")
    
    @staticmethod
    @error_handler
    @log_action("免费克隆")
    async def handle_free_clone(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理免费克隆按钮"""
        if update.callback_query:
            await update.callback_query.answer()
            
        # 从数据库读取免费克隆文案
        clone_message = get_content("free_clone_message", default=settings.free_clone_message)
        
        # 添加联系客服按钮
        keyboard = [[InlineKeyboardButton("👨‍💼 联系客服", callback_data="menu_support")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                clone_message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                clone_message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        
        logger.info(f"用户 {update.effective_user.id} 查看了免费克隆信息")
    
    @staticmethod
    @error_handler
    @log_action("实时U价")
    async def show_usdt_rates(update: Update, context: ContextTypes.DEFAULT_TYPE, channel: str = "all"):
        """显示USDT实时汇率"""
        from src.rates.service import get_or_refresh_rates
        
        if update.callback_query:
            await update.callback_query.answer()
        
        # 获取最新汇率
        rates = await get_or_refresh_rates()
        
        if not rates:
            text = (
                "💵 <b>实时 USDT 汇率</b>\n\n"
                "⚠️ 暂时无法获取汇率信息，请稍后再试。"
            )
            keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="back_to_main")]]
        else:
            # 根据渠道显示不同内容
            if channel == "all":
                text = (
                    f"💵 <b>实时 USDT 汇率</b>\n\n"
                    f"💳 银行卡: {rates.get('bank', 'N/A')} CNY\n"
                    f"📱 支付宝: {rates.get('alipay', 'N/A')} CNY\n"
                    f"💬 微信: {rates.get('wechat', 'N/A')} CNY\n\n"
                    f"更新时间: {rates.get('updated_at', 'N/A')}"
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton("💳 银行卡详情", callback_data="menu_rates_bank"),
                        InlineKeyboardButton("📱 支付宝详情", callback_data="menu_rates_alipay")
                    ],
                    [
                        InlineKeyboardButton("💬 微信详情", callback_data="menu_rates_wechat")
                    ],
                    [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]
                ]
            else:
                # 显示特定渠道的详细商家信息
                channel_names = {
                    "bank": "银行卡",
                    "alipay": "支付宝", 
                    "wechat": "微信"
                }
                
                channel_name = channel_names.get(channel, channel)
                details = rates.get('details', {}).get(channel, {})
                merchants = details.get('merchants', [])[:5]  # 只显示前5个商家
                
                text = f"💵 <b>{channel_name} USDT 汇率详情</b>\n\n"
                
                if merchants:
                    for i, merchant in enumerate(merchants, 1):
                        text += f"{i}. {merchant.get('name', 'N/A')}: {merchant.get('price', 'N/A')} CNY\n"
                else:
                    text += "暂无商家信息\n"
                
                text += f"\n更新时间: {rates.get('updated_at', 'N/A')}"
                
                keyboard = [
                    [InlineKeyboardButton("📊 查看所有", callback_data="menu_rates_all")],
                    [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]
                ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        
        logger.info(f"用户 {update.effective_user.id} 查看了USDT汇率 (channel={channel})")
    
    @staticmethod
    async def show_usdt_rates_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示所有渠道汇率"""
        await SimpleHandlers.show_usdt_rates(update, context, "all")
    
    @staticmethod
    async def show_usdt_rates_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示银行卡汇率"""
        await SimpleHandlers.show_usdt_rates(update, context, "bank")
    
    @staticmethod
    async def show_usdt_rates_alipay(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示支付宝汇率"""
        await SimpleHandlers.show_usdt_rates(update, context, "alipay")
    
    @staticmethod
    async def show_usdt_rates_wechat(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示微信汇率"""
        await SimpleHandlers.show_usdt_rates(update, context, "wechat")


def get_simple_handlers():
    """获取简单功能的处理器列表"""
    return [
        # Reply按钮处理器
        MessageHandler(filters.Regex(r"^👨‍💼 联系客服$"), SimpleHandlers.handle_support),
        MessageHandler(filters.Regex(r"^💵 实时U价$"), SimpleHandlers.show_usdt_rates_all),
        MessageHandler(filters.Regex(r"^🎁 免费克隆$"), SimpleHandlers.handle_free_clone),
        
        # Inline按钮处理器
        CallbackQueryHandler(SimpleHandlers.handle_support, pattern=r'^menu_support$'),
        CallbackQueryHandler(SimpleHandlers.handle_free_clone, pattern=r'^menu_clone$'),
        CallbackQueryHandler(SimpleHandlers.show_usdt_rates_all, pattern=r'^menu_rates_all$'),
        CallbackQueryHandler(SimpleHandlers.show_usdt_rates_bank, pattern=r'^menu_rates_bank$'),
        CallbackQueryHandler(SimpleHandlers.show_usdt_rates_alipay, pattern=r'^menu_rates_alipay$'),
        CallbackQueryHandler(SimpleHandlers.show_usdt_rates_wechat, pattern=r'^menu_rates_wechat$'),
    ]
