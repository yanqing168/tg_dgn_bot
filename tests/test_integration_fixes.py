"""
综合测试：验证Premium和主菜单修复
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, CallbackQuery, Message, Chat
from telegram.ext import ContextTypes, ConversationHandler

from src.premium.handler_v2 import (
    PremiumHandlerV2, 
    SELECTING_TARGET, 
    SELECTING_PACKAGE,
    ENTERING_USERNAME
)
from src.menu.main_menu import MainMenuHandler
from src.payments.order import OrderManager
from src.payments.suffix_manager import SuffixManager
from src.premium.delivery import PremiumDeliveryService


@pytest.fixture
def mock_dependencies():
    """创建所有依赖的模拟对象"""
    bot = AsyncMock()
    bot.send_gift = AsyncMock()
    bot.get_star_transactions = AsyncMock(return_value=[])
    
    order_manager = AsyncMock(spec=OrderManager)
    order_manager.create_order = AsyncMock()
    order_manager.cancel_order = AsyncMock()
    
    suffix_manager = AsyncMock(spec=SuffixManager)
    suffix_manager.get_suffix = AsyncMock(return_value=123)
    
    delivery_service = PremiumDeliveryService(bot, order_manager)
    
    return {
        'bot': bot,
        'order_manager': order_manager,
        'suffix_manager': suffix_manager,
        'delivery_service': delivery_service
    }


@pytest.fixture
def premium_handler(mock_dependencies):
    """创建Premium处理器"""
    return PremiumHandlerV2(
        order_manager=mock_dependencies['order_manager'],
        suffix_manager=mock_dependencies['suffix_manager'],
        delivery_service=mock_dependencies['delivery_service'],
        receive_address="TTestAddress123",
        bot_username="test_bot"
    )


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
class TestIntegratedFixes:
    """综合测试修复功能"""
    
    async def test_premium_flow_without_errors(self, premium_handler, mock_update, mock_context):
        """测试Premium完整流程无错误"""
        # 1. 开始Premium购买
        mock_update.callback_query = None
        result = await premium_handler.start_premium(mock_update, mock_context)
        assert result == SELECTING_TARGET
        
        # 2. 选择给自己开通
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.data = "premium_self"
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        
        result = await premium_handler.select_self(mock_update, mock_context)
        assert result == SELECTING_PACKAGE
        
        # 验证没有错误消息
        calls = mock_update.callback_query.edit_message_text.call_args_list
        for call in calls:
            assert "错误" not in call[0][0]
            assert "失败" not in call[0][0]
        
        # 验证设置了用户数据
        assert mock_context.user_data['recipient_type'] == 'self'
        assert mock_context.user_data['recipient_id'] == 123456
    
    async def test_premium_gift_flow(self, premium_handler, mock_update, mock_context):
        """测试给他人开通Premium流程"""
        # 1. 选择给他人开通
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.data = "premium_other"
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        
        result = await premium_handler.select_other(mock_update, mock_context)
        assert result == ENTERING_USERNAME
        
        # 验证没有错误消息
        calls = mock_update.callback_query.edit_message_text.call_args_list
        for call in calls:
            message = call[0][0]
            if "为他人开通" in message:
                assert "错误" not in message
                assert "失败" not in message
        
        # 验证设置了接收类型
        assert mock_context.user_data['recipient_type'] == 'other'
    
    @patch('src.menu.main_menu.get_content')
    async def test_main_menu_navigation_no_duplicates(self, mock_get_content, mock_update, mock_context):
        """测试主菜单导航无重复提示"""
        mock_get_content.return_value = "欢迎!"
        
        # 1. 首次进入（/start）
        mock_update.callback_query = None
        await MainMenuHandler.start_command(mock_update, mock_context)
        
        # 验证显示了键盘提示
        assert mock_update.message.reply_text.call_count == 2
        first_call_count = mock_update.message.reply_text.call_count
        
        # 重置调用计数
        mock_update.message.reply_text.reset_mock()
        
        # 2. 通过回调返回主菜单
        mock_update.message = None
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.callback_query.message = MagicMock()
        mock_update.callback_query.message.reply_text = AsyncMock()
        
        await MainMenuHandler.show_main_menu(mock_update, mock_context)
        
        # 验证没有重复显示键盘提示
        assert mock_update.callback_query.message.reply_text.call_count == 0
        
        # 3. 再次执行/start应该重新显示
        mock_update.callback_query = None
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        await MainMenuHandler.start_command(mock_update, mock_context)
        
        # 验证重新显示了键盘
        assert mock_update.message.reply_text.call_count == 2
    
    async def test_premium_error_recovery(self, premium_handler, mock_update, mock_context):
        """测试Premium错误恢复"""
        # 模拟网络错误
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        
        # 第一次调用失败，第二次显示错误
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Network timeout")
            return None
        
        mock_update.callback_query.edit_message_text = AsyncMock(side_effect=side_effect)
        
        # 尝试选择给自己开通
        result = await premium_handler.select_self(mock_update, mock_context)
        
        # 验证返回结束状态
        assert result == ConversationHandler.END
        
        # 验证显示了错误消息
        assert call_count == 2  # 第一次失败，第二次显示错误
    
    @patch('src.menu.main_menu.get_content')
    async def test_complete_user_journey(self, mock_get_content, premium_handler, mock_update, mock_context):
        """测试完整用户旅程：start -> premium -> back to main"""
        mock_get_content.return_value = "欢迎!"
        
        # 1. 用户执行/start
        mock_update.callback_query = None
        await MainMenuHandler.start_command(mock_update, mock_context)
        assert mock_context.user_data['main_menu_keyboard_shown'] == True
        
        # 2. 用户点击Premium
        mock_update.message = None
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.data = "menu_premium"
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        
        result = await premium_handler.start_premium(mock_update, mock_context)
        assert result == SELECTING_TARGET
        
        # 3. 用户选择给自己开通
        mock_update.callback_query.data = "premium_self"
        result = await premium_handler.select_self(mock_update, mock_context)
        assert result == SELECTING_PACKAGE
        
        # 4. 用户返回主菜单
        mock_update.callback_query.message = MagicMock()
        mock_update.callback_query.message.reply_text = AsyncMock()
        
        await MainMenuHandler.show_main_menu(mock_update, mock_context)
        
        # 验证没有重复提示（因为之前已经显示过键盘）
        assert mock_update.callback_query.message.reply_text.call_count == 0


@pytest.mark.asyncio
class TestEdgeCases:
    """测试边缘情况"""
    
    async def test_multiple_errors_in_sequence(self, premium_handler, mock_update, mock_context):
        """测试连续多个错误"""
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        
        # 每次调用的第一次失败，第二次成功（显示错误消息）
        call_counts = {'select_self': 0, 'select_other': 0}
        
        def side_effect_self(*args, **kwargs):
            call_counts['select_self'] += 1
            if call_counts['select_self'] == 1:
                raise Exception("Error in select_self")
            return None
        
        def side_effect_other(*args, **kwargs):
            call_counts['select_other'] += 1
            if call_counts['select_other'] == 1:
                raise Exception("Error in select_other")
            return None
        
        # 第一次错误
        mock_update.callback_query.edit_message_text = AsyncMock(side_effect=side_effect_self)
        result1 = await premium_handler.select_self(mock_update, mock_context)
        assert result1 == ConversationHandler.END
        
        # 第二次错误（不同的操作）
        mock_update.callback_query.edit_message_text = AsyncMock(side_effect=side_effect_other)
        result2 = await premium_handler.select_other(mock_update, mock_context)
        assert result2 == ConversationHandler.END
    
    @patch('src.menu.main_menu.get_content')
    async def test_keyboard_state_persistence(self, mock_get_content, mock_update, mock_context):
        """测试键盘状态持久性"""
        mock_get_content.return_value = "Test"
        
        # 设置初始状态
        mock_update.callback_query = None
        context_data = {}
        mock_context.user_data = context_data
        
        # 第一次显示
        await MainMenuHandler.show_main_menu(mock_update, mock_context)
        assert context_data.get('main_menu_keyboard_shown') == True
        
        # 模拟用户数据保存和恢复
        saved_data = dict(context_data)
        
        # 创建新的上下文但使用保存的数据
        mock_context.user_data = saved_data
        
        # 再次显示主菜单
        mock_update.message.reply_text.reset_mock()
        await MainMenuHandler.show_main_menu(mock_update, mock_context)
        
        # 验证没有重复显示（因为标志位被保留）
        keyboard_messages = [
            call for call in mock_update.message.reply_text.call_args_list
            if "使用下方按钮" in str(call)
        ]
        assert len(keyboard_messages) == 0


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
