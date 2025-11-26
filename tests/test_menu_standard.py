"""
测试标准化的主菜单模块
重点验证键盘提示不重复的问题
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, CallbackQuery, Message, Chat, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from src.modules.menu.handler import MainMenuModule
from src.modules.menu.messages import MainMenuMessages
from src.core.state_manager import ModuleStateManager


class MockContext:
    """模拟Context对象"""
    def __init__(self):
        self.user_data = {}
        self.chat_data = {}
        self.bot_data = {}


def create_mock_update(callback_data=None, message_text=None, command=None):
    """创建模拟的Update对象"""
    update = MagicMock(spec=Update)
    
    # 创建用户
    user = MagicMock(spec=User)
    user.id = 123456
    user.username = "testuser"
    user.first_name = "Test"
    user.is_bot = False
    
    # 创建聊天
    chat = MagicMock(spec=Chat)
    chat.id = 123456
    chat.type = "private"
    
    # 创建消息
    message = MagicMock(spec=Message)
    message.chat = chat
    message.from_user = user
    message.reply_text = AsyncMock()
    message.text = message_text or command
    
    # 设置回调查询
    if callback_data:
        callback_query = MagicMock(spec=CallbackQuery)
        callback_query.from_user = user
        callback_query.message = message
        callback_query.data = callback_data
        callback_query.answer = AsyncMock()
        callback_query.edit_message_text = AsyncMock()
        update.callback_query = callback_query
        update.message = None
    else:
        update.callback_query = None
        update.message = message
    
    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message
    
    return update


@pytest.fixture
def menu_module():
    """创建主菜单模块实例"""
    return MainMenuModule()


class TestMainMenuStandard:
    """测试标准化的主菜单模块"""
    
    def test_module_properties(self, menu_module):
        """测试模块属性"""
        assert menu_module.module_name == "main_menu"
        handlers = menu_module.get_handlers()
        assert len(handlers) == 3  # start命令 + 返回主菜单回调 + 免费克隆回调
    
    @pytest.mark.asyncio
    @patch('src.config.settings')
    @patch('src.modules.menu.handler.get_content')
    async def test_start_command_shows_keyboard_once(self, mock_get_content, mock_settings, menu_module):
        """测试/start命令只显示一次键盘提示"""
        # 设置模拟内容
        mock_get_content.return_value = "欢迎使用 {first_name}!"
        mock_settings.welcome_message = "欢迎使用 {first_name}!"
        mock_settings.promotion_buttons = '[]'  # 空按钮配置
        
        update = create_mock_update(command="/start")
        context = MockContext()
        
        # 执行/start命令
        await menu_module.start_command(update, context)
        
        # 验证发送了两条消息
        assert update.message.reply_text.call_count == 2
        
        # 验证第一条是欢迎消息
        first_call = update.message.reply_text.call_args_list[0]
        assert "欢迎使用" in first_call[0][0]
        assert first_call[1]['parse_mode'] == 'HTML'
        
        # 验证第二条是键盘提示
        second_call = update.message.reply_text.call_args_list[1]
        assert MainMenuMessages.KEYBOARD_HINT in second_call[0][0]
        
        # 验证设置了标志位
        assert context.user_data['main_menu_keyboard_shown'] == True
    
    @pytest.mark.asyncio
    async def test_callback_return_no_keyboard_hint(self, menu_module):
        """测试从回调返回主菜单不会显示键盘提示"""
        update = create_mock_update(callback_data="back_to_main")
        context = MockContext()
        # 模拟用户已经有键盘
        context.user_data['main_menu_keyboard_shown'] = True
        
        # 执行返回主菜单
        await menu_module.show_main_menu(update, context)
        
        # 验证只调用了edit_message_text，没有发送新消息
        assert update.callback_query.edit_message_text.call_count == 1
        assert update.callback_query.message.reply_text.call_count == 0
        
        # 验证消息内容
        call_args = update.callback_query.edit_message_text.call_args
        assert MainMenuMessages.MAIN_MENU in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'HTML'
    
    @pytest.mark.asyncio
    async def test_callback_first_time_no_keyboard(self, menu_module):
        """测试第一次从回调进入也不会显示键盘（因为是回调）"""
        update = create_mock_update(callback_data="back_to_main")
        context = MockContext()
        # 用户没有键盘标志
        
        await menu_module.show_main_menu(update, context)
        
        # 验证没有发送键盘提示
        assert update.callback_query.edit_message_text.call_count == 1
        assert update.callback_query.message.reply_text.call_count == 0
    
    @pytest.mark.asyncio
    async def test_direct_call_first_time_shows_keyboard(self, menu_module):
        """测试直接调用（非回调）第一次会显示键盘"""
        update = create_mock_update(message_text="返回主菜单")
        context = MockContext()
        # 用户没有键盘标志
        
        await menu_module.show_main_menu(update, context)
        
        # 验证发送了两条消息
        assert update.message.reply_text.call_count == 2
        
        # 第一条是主菜单
        first_call = update.message.reply_text.call_args_list[0]
        assert MainMenuMessages.MAIN_MENU in first_call[0][0]
        
        # 第二条是键盘提示
        second_call = update.message.reply_text.call_args_list[1]
        assert MainMenuMessages.KEYBOARD_HINT in second_call[0][0]
        
        # 验证设置了标志
        assert context.user_data['main_menu_keyboard_shown'] == True
    
    @pytest.mark.asyncio
    async def test_direct_call_with_keyboard_no_hint(self, menu_module):
        """测试直接调用但已有键盘时不显示提示"""
        update = create_mock_update(message_text="返回主菜单")
        context = MockContext()
        context.user_data['main_menu_keyboard_shown'] = True
        
        await menu_module.show_main_menu(update, context)
        
        # 验证只发送了主菜单，没有键盘提示
        assert update.message.reply_text.call_count == 1
        call_args = update.message.reply_text.call_args
        assert MainMenuMessages.MAIN_MENU in call_args[0][0]
    
    @pytest.mark.asyncio
    @patch('src.config.settings')
    @patch('src.modules.menu.handler.get_content')
    async def test_start_command_resets_flag(self, mock_get_content, mock_settings, menu_module):
        """测试/start命令会重置键盘标志"""
        mock_get_content.return_value = "欢迎!"
        mock_settings.welcome_message = "欢迎!"
        mock_settings.promotion_buttons = '[]'
        
        update = create_mock_update(command="/start")
        context = MockContext()
        # 先设置标志为True
        context.user_data['main_menu_keyboard_shown'] = True
        
        await menu_module.start_command(update, context)
        
        # 验证发送了键盘（说明标志被重置了）
        assert update.message.reply_text.call_count == 2
        # 最终标志应该是True（经历了False->True）
        assert context.user_data['main_menu_keyboard_shown'] == True
    
    @pytest.mark.asyncio
    async def test_edit_message_failure_fallback(self, menu_module):
        """测试编辑消息失败时的回退处理"""
        update = create_mock_update(callback_data="back_to_main")
        context = MockContext()
        
        # 模拟编辑失败
        update.callback_query.edit_message_text.side_effect = Exception("Message not modified")
        
        await menu_module.show_main_menu(update, context)
        
        # 验证尝试了编辑
        assert update.callback_query.edit_message_text.call_count == 1
        
        # 验证回退到发送新消息（但仍然不发送键盘提示）
        assert update.callback_query.message.reply_text.call_count == 1
        call_args = update.callback_query.message.reply_text.call_args
        assert MainMenuMessages.MAIN_MENU in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_cleanup_awaiting_address(self, menu_module):
        """测试返回主菜单会清理等待状态"""
        update = create_mock_update(callback_data="back_to_main")
        context = MockContext()
        # 设置等待地址状态
        context.user_data['awaiting_address'] = True
        context.user_data['some_other_data'] = "test"
        
        await menu_module.show_main_menu(update, context)
        
        # 验证清理了awaiting_address
        assert 'awaiting_address' not in context.user_data
        # 验证其他数据未被清理
        assert context.user_data.get('some_other_data') == "test"
    
    @pytest.mark.asyncio
    @patch('src.config.settings')
    @patch('src.modules.menu.handler.get_content')
    async def test_handle_free_clone(self, mock_get_content, mock_settings, menu_module):
        """测试免费克隆功能处理"""
        mock_get_content.return_value = "免费克隆功能"
        mock_settings.free_clone_message = "免费克隆功能"
        
        update = create_mock_update(callback_data="menu_clone")
        context = MockContext()
        
        await menu_module.handle_free_clone(update, context)
        
        # 验证回答了查询
        update.callback_query.answer.assert_called_once()
        
        # 验证编辑了消息
        call_args = update.callback_query.edit_message_text.call_args
        assert "免费克隆功能" in call_args[0][0]
        assert call_args[1]['parse_mode'] == 'HTML'
        
        # 验证有返回主菜单按钮
        reply_markup = call_args[1]['reply_markup']
        buttons = reply_markup.inline_keyboard
        assert any("返回主菜单" in str(btn) for row in buttons for btn in row)
    
    def test_build_reply_keyboard(self, menu_module):
        """测试构建回复键盘"""
        keyboard = menu_module._build_reply_keyboard()
        
        # 验证是ReplyKeyboardMarkup类型
        assert isinstance(keyboard, ReplyKeyboardMarkup)
        
        # 验证键盘按钮数量（4x2布局）
        assert len(keyboard.keyboard) == 4
        assert len(keyboard.keyboard[0]) == 2
        
        # 验证包含主要功能
        button_texts = []
        for row in keyboard.keyboard:
            for button in row:
                button_texts.append(button.text)
        
        assert "💎 Premium会员" in button_texts
        assert "⚡ 能量兑换" in button_texts
        assert "🔍 地址查询" in button_texts
        assert "👤 个人中心" in button_texts


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
