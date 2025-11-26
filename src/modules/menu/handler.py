"""
主菜单模块主处理器 - 标准化版本
解决了返回主菜单重复提示的问题
"""

import logging
import json
from typing import List, Optional
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ContextTypes,
    BaseHandler,
    CommandHandler,
    CallbackQueryHandler
)

from src.core.base import BaseModule
from src.core.formatter import MessageFormatter
from src.core.state_manager import ModuleStateManager
from src.utils.content_helper import get_content

from .messages import MainMenuMessages


logger = logging.getLogger(__name__)


class MainMenuModule(BaseModule):
    """标准化的主菜单模块"""
    
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
    
    def __init__(self):
        """初始化主菜单模块"""
        self.formatter = MessageFormatter()
        self.state_manager = ModuleStateManager()
        self.keyboard_shown_key = "main_menu_keyboard_shown"
    
    @property
    def module_name(self) -> str:
        """模块名称"""
        return "main_menu"
    
    def get_handlers(self) -> List[BaseHandler]:
        """获取模块处理器"""
        return [
            CommandHandler("start", self.start_command),
            CallbackQueryHandler(self.show_main_menu, pattern=r"^(back_to_main|nav_back_to_main|menu_back_to_main)$"),
            CallbackQueryHandler(self.handle_free_clone, pattern=r"^menu_clone$"),
        ]
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理 /start 命令"""
        from src.config import settings
        
        user = update.effective_user
        
        # 重要：重置键盘显示标志，因为/start是新的会话开始
        context.user_data[self.keyboard_shown_key] = False
        
        # 从数据库读取欢迎语（支持热更新）
        text = get_content("welcome_message", default=settings.welcome_message)
        text = text.replace("{first_name}", self.formatter.escape_html(user.first_name or "朋友"))
        
        # 构建引流按钮（InlineKeyboard）
        inline_keyboard = self._build_promotion_buttons()
        inline_markup = InlineKeyboardMarkup(inline_keyboard)
        
        # 构建底部键盘（ReplyKeyboard）
        reply_markup = self._build_reply_keyboard()
        
        # 先发送带InlineKeyboard的欢迎消息
        await update.message.reply_text(
            text, 
            parse_mode="HTML", 
            reply_markup=inline_markup
        )
        
        # 然后设置底部键盘并发送提示
        # 注意：只在/start命令时发送键盘提示
        await update.message.reply_text(
            MainMenuMessages.KEYBOARD_HINT,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        context.user_data[self.keyboard_shown_key] = True
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        显示主菜单（从回调返回）
        关键修复：从回调返回时不再重复发送键盘提示
        """
        # 清理可能的临时状态（如地址查询等待状态）
        context.user_data.pop("awaiting_address", None)
        
        # 构建菜单
        keyboard = self._build_promotion_buttons()
        inline_reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = MainMenuMessages.MAIN_MENU
        
        query = update.callback_query
        if query:
            await query.answer()
            try:
                # 只更新消息内容，不发送新消息
                await query.edit_message_text(
                    text, 
                    parse_mode="HTML", 
                    reply_markup=inline_reply_markup
                )
            except Exception as e:
                # 如果编辑失败（比如消息太旧），发送新消息
                logger.warning(f"编辑消息失败: {e}")
                await query.message.reply_text(
                    text, 
                    parse_mode="HTML", 
                    reply_markup=inline_reply_markup
                )
            
            # 关键：从回调返回主菜单时，不再发送键盘提示
            # 因为ReplyKeyboard是持久的，用户已经有了
            # 这就解决了重复提示的问题
        else:
            # 如果不是从回调触发（比如直接调用）
            message = update.message or update.effective_message
            if not message:
                return
            
            await message.reply_text(
                text, 
                parse_mode="HTML", 
                reply_markup=inline_reply_markup
            )
            
            # 只有在用户没有键盘时才显示
            # 比如新用户或者bot重启后的第一次
            if not context.user_data.get(self.keyboard_shown_key):
                reply_markup = self._build_reply_keyboard()
                await message.reply_text(
                    MainMenuMessages.KEYBOARD_HINT,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                context.user_data[self.keyboard_shown_key] = True
    
    async def handle_free_clone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理免费克隆功能"""
        from src.config import settings
        
        query = update.callback_query
        await query.answer()
        
        # 从数据库读取免费克隆文案（支持热更新）
        text = get_content("free_clone_message", default=settings.free_clone_message)
        
        keyboard = [
            [InlineKeyboardButton("👨‍💼 联系客服", callback_data="menu_support")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text, 
            parse_mode="HTML", 
            reply_markup=reply_markup
        )
    
    def _build_promotion_buttons(self) -> List[List[InlineKeyboardButton]]:
        """构建引流按钮（从配置读取）"""
        from src.config import settings
        
        try:
            # 解析配置的按钮
            buttons_config = settings.promotion_buttons
            # 移除换行和多余空格
            buttons_config = buttons_config.replace('\n', '').replace(' ', '')
            # 解析为列表（安全地使用JSON）
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
    
    def _build_reply_keyboard(self) -> ReplyKeyboardMarkup:
        """构建底部回复键盘"""
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
