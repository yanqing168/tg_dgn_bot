"""
Telegram 模拟器 - 用于集成测试
模拟真实的 Telegram Update 和 CallbackQuery，不需要网络连接
"""
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from unittest.mock import MagicMock, AsyncMock
from telegram import (
    Update, User, Message, Chat, CallbackQuery, 
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import Application, ContextTypes


class TelegramSimulator:
    """Telegram 交互模拟器"""
    
    def __init__(self, user_id: int = 123456789, username: str = "test_user"):
        """
        初始化模拟器
        
        Args:
            user_id: 模拟用户ID
            username: 模拟用户名
        """
        self.user_id = user_id
        self.username = username
        self.message_id_counter = 1000
        self.update_id_counter = 1
        self.chat_id = user_id  # 私聊中 chat_id = user_id
        
        # 创建模拟用户
        self.user = self._create_user()
        self.chat = self._create_chat()
        
        # 消息历史记录
        self.message_history: List[Message] = []
        self.last_bot_message: Optional[Message] = None
        
    def _create_user(self) -> User:
        """创建模拟用户"""
        return User(
            id=self.user_id,
            username=self.username,
            first_name="Test",
            last_name="User",
            is_bot=False
        )
    
    def _create_chat(self) -> Chat:
        """创建模拟聊天"""
        return Chat(
            id=self.chat_id,
            type="private",
            username=self.username,
            first_name="Test",
            last_name="User"
        )
    
    def create_message_update(self, text: str) -> Update:
        """
        创建文本消息更新
        
        Args:
            text: 消息文本
            
        Returns:
            Update 对象
        """
        self.message_id_counter += 1
        self.update_id_counter += 1
        
        # 使用 MagicMock 创建 message（python-telegram-bot v21 的 Message 是 frozen dataclass）
        message = MagicMock(spec=Message)
        message.message_id = self.message_id_counter
        message.date = datetime.now()
        message.chat = self.chat
        message.from_user = self.user
        message.text = text
        message.chat_id = self.chat_id
        
        # 设置 reply_text 等方法为 AsyncMock
        message.reply_text = AsyncMock(side_effect=self._handle_reply_text)
        message.reply_html = AsyncMock(side_effect=self._handle_reply_html)
        message.reply_markdown = AsyncMock(side_effect=self._handle_reply_markdown)
        message.reply_markdown_v2 = AsyncMock(side_effect=self._handle_reply_markdown_v2)
        message.delete = AsyncMock()
        
        self.message_history.append(message)
        
        update = Update(
            update_id=self.update_id_counter,
            message=message
        )
        
        return update
    
    def create_callback_query_update(self, callback_data: str, message: Optional[Message] = None) -> Update:
        """
        创建回调查询更新
        
        Args:
            callback_data: 回调数据
            message: 关联的消息（如果为None，使用最后一条bot消息）
            
        Returns:
            Update 对象
        """
        self.update_id_counter += 1
        
        if message is None:
            message = self.last_bot_message or self._create_bot_message("测试消息")
        
        # 使用 MagicMock（python-telegram-bot v21 的 CallbackQuery 是 frozen dataclass）
        callback_query = MagicMock(spec=CallbackQuery)
        callback_query.id = str(self.update_id_counter)
        callback_query.from_user = self.user
        callback_query.chat_instance = str(self.chat_id)
        callback_query.data = callback_data
        callback_query.message = message
        
        # 设置回调查询的方法
        callback_query.answer = AsyncMock()
        callback_query.edit_message_text = AsyncMock(side_effect=self._handle_edit_message_text)
        callback_query.edit_message_reply_markup = AsyncMock()
        callback_query.delete_message = AsyncMock()
        
        update = Update(
            update_id=self.update_id_counter,
            callback_query=callback_query
        )
        
        return update
    
    def create_command_update(self, command: str, args: str = "") -> Update:
        """
        创建命令更新
        
        Args:
            command: 命令名（不含/）
            args: 命令参数
            
        Returns:
            Update 对象
        """
        text = f"/{command}"
        if args:
            text += f" {args}"
        return self.create_message_update(text)
    
    def _create_bot_message(self, text: str, reply_markup=None) -> MagicMock:
        """创建bot消息（用于回调查询）"""
        self.message_id_counter += 1
        
        bot_user = User(
            id=1234567890,
            username="test_bot",
            first_name="Test Bot",
            is_bot=True
        )
        
        # 使用 MagicMock（python-telegram-bot v21 的 Message 是 frozen dataclass）
        message = MagicMock(spec=Message)
        message.message_id = self.message_id_counter
        message.date = datetime.now()
        message.chat = self.chat
        message.from_user = bot_user
        message.text = text
        message.chat_id = self.chat_id
        message.reply_markup = reply_markup
        
        # 设置消息方法
        message.edit_text = AsyncMock(side_effect=self._handle_edit_message_text)
        message.edit_reply_markup = AsyncMock()
        message.delete = AsyncMock()
        
        return message
    
    async def _handle_reply_text(self, text: str, **kwargs):
        """处理 reply_text 调用"""
        self.last_bot_message = self._create_bot_message(text, kwargs.get('reply_markup'))
        print(f"[BOT -> {self.username}]: {text}")
        
        # 如果有 reply_markup，打印按钮
        if 'reply_markup' in kwargs:
            self._print_keyboard(kwargs['reply_markup'])
        
        return self.last_bot_message
    
    async def _handle_reply_html(self, text: str, **kwargs):
        """处理 reply_html 调用"""
        return await self._handle_reply_text(text, **kwargs)
    
    async def _handle_reply_markdown(self, text: str, **kwargs):
        """处理 reply_markdown 调用"""
        return await self._handle_reply_text(text, **kwargs)
    
    async def _handle_reply_markdown_v2(self, text: str, **kwargs):
        """处理 reply_markdown_v2 调用"""
        return await self._handle_reply_text(text, **kwargs)
    
    async def _handle_edit_message_text(self, text: str, **kwargs):
        """处理 edit_message_text 调用"""
        print(f"[BOT EDIT]: {text}")
        
        # 更新 last_bot_message（关键修复）
        self.last_bot_message = self._create_bot_message(text, kwargs.get('reply_markup'))
        
        # 如果有 reply_markup，打印按钮
        if 'reply_markup' in kwargs:
            self._print_keyboard(kwargs['reply_markup'])
        
        return self.last_bot_message
    
    def _print_keyboard(self, keyboard):
        """打印键盘布局"""
        if isinstance(keyboard, InlineKeyboardMarkup):
            print("  [Inline Keyboard]:")
            for row in keyboard.inline_keyboard:
                buttons = []
                for btn in row:
                    if btn.callback_data:
                        buttons.append(f"{btn.text} ({btn.callback_data})")
                    elif btn.url:
                        buttons.append(f"{btn.text} -> {btn.url}")
                print(f"    {' | '.join(buttons)}")
        elif isinstance(keyboard, ReplyKeyboardMarkup):
            print("  [Reply Keyboard]:")
            for row in keyboard.keyboard:
                buttons = []
                for btn in row:
                    if isinstance(btn, KeyboardButton):
                        buttons.append(btn.text)
                    else:
                        buttons.append(str(btn))
                print(f"    {' | '.join(buttons)}")
    
    def extract_inline_buttons(self, message: Message) -> Dict[str, str]:
        """
        提取消息中的内联键盘按钮
        
        Returns:
            {button_text: callback_data} 字典
        """
        buttons = {}
        if hasattr(message, 'reply_markup') and message.reply_markup:
            if isinstance(message.reply_markup, InlineKeyboardMarkup):
                for row in message.reply_markup.inline_keyboard:
                    for btn in row:
                        if btn.callback_data:
                            buttons[btn.text] = btn.callback_data
        return buttons


class BotTestHelper:
    """Bot 测试辅助类"""
    
    def __init__(self, application: Application):
        """
        初始化测试辅助类
        
        Args:
            application: Bot Application 实例
        """
        self.app = application
        self.simulator = TelegramSimulator()
        self.context = None
        
    async def initialize(self):
        """初始化应用（离线模式，不连接 Telegram API）"""
        # 设置 Application 的内部初始化状态，绕过检查
        # python-telegram-bot v21 使用 _initialized 属性
        self.app._initialized = True
        
        # 创建模拟 context
        self.context = MagicMock()
        self.context.bot = self.app.bot
        self.context.bot_data = {}
        self.context.chat_data = {}
        self.context.user_data = {}
        
    async def shutdown(self):
        """关闭应用（离线模式）"""
        # 不调用 app.stop() / app.shutdown()，避免网络操作
        pass
    
    async def send_command(self, command: str, args: str = "") -> Any:
        """
        发送命令
        
        Args:
            command: 命令名（不含/）
            args: 命令参数
        """
        print(f"\n[USER]: /{command} {args}".strip())
        update = self.simulator.create_command_update(command, args)
        return await self.app.process_update(update)
    
    async def send_message(self, text: str) -> Any:
        """
        发送文本消息
        
        Args:
            text: 消息文本
        """
        print(f"\n[USER]: {text}")
        update = self.simulator.create_message_update(text)
        return await self.app.process_update(update)
    
    async def click_button(self, callback_data: str) -> Any:
        """
        点击内联键盘按钮
        
        Args:
            callback_data: 回调数据
        """
        print(f"\n[USER CLICK]: {callback_data}")
        update = self.simulator.create_callback_query_update(callback_data)
        return await self.app.process_update(update)
    
    async def click_button_by_text(self, button_text: str) -> Any:
        """
        通过按钮文本点击按钮
        
        Args:
            button_text: 按钮文本
        """
        buttons = self.simulator.extract_inline_buttons(self.simulator.last_bot_message)
        if button_text in buttons:
            return await self.click_button(buttons[button_text])
        else:
            raise ValueError(f"Button '{button_text}' not found. Available: {list(buttons.keys())}")
    
    def get_last_message(self) -> Optional[Message]:
        """获取最后一条bot消息"""
        return self.simulator.last_bot_message
    
    def get_message_text(self) -> Optional[str]:
        """获取最后一条bot消息的文本"""
        if self.simulator.last_bot_message:
            return self.simulator.last_bot_message.text
        return None
