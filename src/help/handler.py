"""增强的帮助系统处理器"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler
)
from loguru import logger

from .content import (
    MAIN_HELP_TEXT,
    BASIC_HELP,
    PAYMENT_HELP,
    SERVICES_HELP,
    QUERY_HELP,
    FAQ_CONTENT,
    QUICK_START
)

# 对话状态
SHOWING_HELP = 1


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理 /help 命令 - 显示帮助主菜单"""
    user = update.effective_user
    logger.info(f"用户 {user.id} 请求帮助")
    
    keyboard = [
        [
            InlineKeyboardButton("📖 基础功能", callback_data="help_basic"),
            InlineKeyboardButton("💳 支付充值", callback_data="help_payment")
        ],
        [
            InlineKeyboardButton("🎁 服务使用", callback_data="help_services"),
            InlineKeyboardButton("🔍 查询功能", callback_data="help_query")
        ],
        [
            InlineKeyboardButton("❓ 常见问题", callback_data="help_faq"),
            InlineKeyboardButton("🚀 快速开始", callback_data="help_quick")
        ],
        [
            InlineKeyboardButton("🏠 返回主菜单", callback_data="back_to_main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        MAIN_HELP_TEXT,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    
    return SHOWING_HELP


async def show_help_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """显示具体分类的帮助内容"""
    query = update.callback_query
    await query.answer()
    
    # 获取分类
    category = query.data.replace("help_", "")
    
    # 内容映射
    content_map = {
        "basic": BASIC_HELP,
        "payment": PAYMENT_HELP,
        "services": SERVICES_HELP,
        "query": QUERY_HELP,
        "faq": FAQ_CONTENT,
        "quick": QUICK_START
    }
    
    content = content_map.get(category, MAIN_HELP_TEXT)
    
    # 返回按钮
    keyboard = [
        [InlineKeyboardButton("◀️ 返回帮助菜单", callback_data="help_back")],
        [InlineKeyboardButton("🏠 返回主菜单", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(
            content,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.warning(f"编辑帮助消息失败: {e}")
        await query.message.reply_text(
            content,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    
    return SHOWING_HELP


async def help_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """返回帮助主菜单"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("📖 基础功能", callback_data="help_basic"),
            InlineKeyboardButton("💳 支付充值", callback_data="help_payment")
        ],
        [
            InlineKeyboardButton("🎁 服务使用", callback_data="help_services"),
            InlineKeyboardButton("🔍 查询功能", callback_data="help_query")
        ],
        [
            InlineKeyboardButton("❓ 常见问题", callback_data="help_faq"),
            InlineKeyboardButton("🚀 快速开始", callback_data="help_quick")
        ],
        [
            InlineKeyboardButton("🏠 返回主菜单", callback_data="back_to_main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(
            MAIN_HELP_TEXT,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.warning(f"编辑帮助菜单失败: {e}")
        await query.message.reply_text(
            MAIN_HELP_TEXT,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    
    return SHOWING_HELP


async def back_to_main_from_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """从帮助系统返回主菜单"""
    query = update.callback_query
    await query.answer()

    # 导入主菜单处理器
    from src.menu.main_menu import MainMenuHandler

    # 显示主菜单
    await MainMenuHandler.show_main_menu(update, context)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """取消帮助对话 - 使用统一清理机制"""
    from src.common.navigation_manager import NavigationManager
    
    # 先发送取消确认
    if update.callback_query:
        await update.callback_query.answer("已取消")
    
    # 使用统一的清理和导航方法
    return await NavigationManager.cleanup_and_show_main_menu(update, context)


def get_help_handler() -> ConversationHandler:
    """
    获取增强的帮助系统 ConversationHandler
    
    支持功能：
    - 分类帮助（基础/支付/服务/查询）
    - FAQ 常见问题
    - 快速开始指南
    - 导航返回功能
    """
    return ConversationHandler(
        entry_points=[
            CommandHandler("help", help_command)
        ],
        states={
            SHOWING_HELP: [
                CallbackQueryHandler(show_help_category, pattern=r"^help_(basic|payment|services|query|faq|quick)$"),
                CallbackQueryHandler(help_back, pattern=r"^help_back$"),
                CallbackQueryHandler(back_to_main_from_help, pattern=r"^back_to_main$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(back_to_main_from_help, pattern=r"^back_to_main$"),
            CommandHandler("cancel", cancel)
        ],
        per_chat=True,
        per_user=True,
        per_message=False,
    )
