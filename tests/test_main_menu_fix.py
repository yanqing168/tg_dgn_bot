"""
测试主菜单重复提示修复
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, CallbackQuery, Message, Chat, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from src.menu.main_menu import MainMenuHandler


@pytest.fixture
def mock_update():
    """创建模拟Update对象"""
    update = MagicMock(spec=Update)
    
    # 设置用户
    user = MagicMock(spec=User)
    user.id = 123456
    user.username = "testuser"
    user.first_name = "Test"
    user.is_bot = False
    
    # 设置聊天
    chat = MagicMock(spec=Chat)
    chat.id = 123456
    chat.type = "private"
    
    # 设置消息
    message = MagicMock(spec=Message)
    message.chat = chat
    message.from_user = user
    message.reply_text = AsyncMock()
    
    # 设置回调查询
    callback_query = MagicMock(spec=CallbackQuery)
    callback_query.from_user = user
    callback_query.message = message
    callback_query.data = None
    callback_query.answer = AsyncMock()
    callback_query.edit_message_text = AsyncMock()
    
    update.effective_user = user
    update.effective_chat = chat
    update.message = message
    update.callback_query = None
    update.effective_message = message
    
    return update


@pytest.fixture
def mock_context():
    """创建模拟Context对象"""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.chat_data = {}
    context.bot_data = {}
    return context


@pytest.mark.asyncio
class TestMainMenuFix:
    """测试主菜单修复"""
    
    @patch('src.menu.main_menu.get_content')
    async def test_start_command_shows_keyboard_once(self, mock_get_content, mock_update, mock_context):
        """测试/start命令只显示一次键盘提示"""
        # 设置模拟内容
        mock_get_content.return_value = "欢迎使用 {first_name}!"
        
        # 执行/start命令
        await MainMenuHandler.start_command(mock_update, mock_context)
        
        # 验证发送了两条消息
        assert mock_update.message.reply_text.call_count == 2
        
        # 验证第二条消息是键盘提示
        calls = mock_update.message.reply_text.call_args_list
        keyboard_call = calls[1]
        assert "使用下方按钮快速访问功能" in keyboard_call[0][0]
        
        # 验证设置了标志位
        assert mock_context.user_data['main_menu_keyboard_shown'] == True
    
    @patch('src.menu.main_menu.get_content')
    async def test_show_main_menu_callback_no_duplicate(self, mock_get_content, mock_update, mock_context):
        """测试通过回调返回主菜单不会重复提示"""
        # 设置为回调查询
        mock_update.message = None
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.callback_query.message = MagicMock()
        mock_update.callback_query.message.reply_text = AsyncMock()
        
        # 第一次显示主菜单
        await MainMenuHandler.show_main_menu(mock_update, mock_context)
        
        # 验证第一次显示了键盘提示
        assert mock_update.callback_query.message.reply_text.call_count == 1
        assert mock_context.user_data['main_menu_keyboard_shown'] == True
        
        # 重置调用计数
        mock_update.callback_query.message.reply_text.reset_mock()
        
        # 第二次显示主菜单（模拟返回）
        await MainMenuHandler.show_main_menu(mock_update, mock_context)
        
        # 验证没有再次显示键盘提示
        assert mock_update.callback_query.message.reply_text.call_count == 0
    
    @patch('src.menu.main_menu.get_content')
    async def test_show_main_menu_message_first_time(self, mock_get_content, mock_update, mock_context):
        """测试通过消息显示主菜单第一次会显示键盘"""
        # 设置为消息触发
        mock_update.callback_query = None
        
        # 第一次显示主菜单
        await MainMenuHandler.show_main_menu(mock_update, mock_context)
        
        # 验证显示了键盘提示
        assert mock_update.message.reply_text.call_count == 2
        calls = mock_update.message.reply_text.call_args_list
        keyboard_call = calls[1]
        assert "使用下方按钮快速访问功能" in keyboard_call[0][0]
        assert mock_context.user_data['main_menu_keyboard_shown'] == True
    
    @patch('src.menu.main_menu.get_content')
    async def test_start_command_resets_flag(self, mock_get_content, mock_update, mock_context):
        """测试/start命令会重置键盘显示标志"""
        # 设置模拟内容
        mock_get_content.return_value = "欢迎!"
        
        # 先设置标志位为True（模拟之前已经显示过）
        mock_context.user_data['main_menu_keyboard_shown'] = True
        
        # 执行/start命令
        await MainMenuHandler.start_command(mock_update, mock_context)
        
        # 验证重新显示了键盘
        assert mock_update.message.reply_text.call_count == 2
        
        # 验证标志位仍然为True（但经历了False->True的过程）
        assert mock_context.user_data['main_menu_keyboard_shown'] == True
    
    @patch('src.menu.main_menu.get_content')
    async def test_callback_error_handling(self, mock_get_content, mock_update, mock_context):
        """测试回调查询中edit_message_text失败的处理"""
        # 设置为回调查询
        mock_update.message = None
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock(side_effect=Exception("Message not modified"))
        mock_update.callback_query.message = MagicMock()
        mock_update.callback_query.message.reply_text = AsyncMock()
        
        # 显示主菜单
        await MainMenuHandler.show_main_menu(mock_update, mock_context)
        
        # 验证调用了edit_message_text
        assert mock_update.callback_query.edit_message_text.call_count == 1
        
        # 验证fallback到reply_text（因为edit失败）
        assert mock_update.callback_query.message.reply_text.call_count >= 1
    
    async def test_cleanup_awaiting_address(self, mock_update, mock_context):
        """测试返回主菜单会清理等待地址状态"""
        # 设置等待地址状态
        mock_context.user_data['awaiting_address'] = True
        mock_context.user_data['some_other_data'] = "test"
        
        # 显示主菜单
        await MainMenuHandler.show_main_menu(mock_update, mock_context)
        
        # 验证清理了awaiting_address
        assert 'awaiting_address' not in mock_context.user_data
        
        # 验证其他数据未被清理
        assert mock_context.user_data.get('some_other_data') == "test"


class TestKeyboardBuilders:
    """测试键盘构建器"""
    
    def test_build_reply_keyboard(self):
        """测试构建回复键盘"""
        keyboard = MainMenuHandler._build_reply_keyboard()
        
        # 验证是ReplyKeyboardMarkup类型
        assert isinstance(keyboard, ReplyKeyboardMarkup)
        
        # 验证键盘按钮数量（4x2布局）
        assert len(keyboard.keyboard) == 4
        assert len(keyboard.keyboard[0]) == 2
        assert len(keyboard.keyboard[1]) == 2
        assert len(keyboard.keyboard[2]) == 2
        assert len(keyboard.keyboard[3]) == 2
    
    def test_build_promotion_buttons(self):
        """测试构建推广按钮"""
        buttons = MainMenuHandler._build_promotion_buttons()
        
        # 验证返回列表
        assert isinstance(buttons, list)
        
        # 验证包含基本功能按钮
        button_texts = []
        for row in buttons:
            for button in row:
                button_texts.append(button.text)
        
        # 验证包含主要功能
        assert any("Premium" in text or "会员" in text for text in button_texts)
        assert any("个人中心" in text or "余额" in text for text in button_texts)


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
