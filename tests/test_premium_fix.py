"""
测试Premium会员开通功能修复
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from telegram import Update, User, CallbackQuery, Message, Chat
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime, timedelta
import uuid

from src.premium.handler_v2 import (
    PremiumHandlerV2, 
    SELECTING_TARGET,
    SELECTING_PACKAGE,
    ENTERING_USERNAME,
    AWAITING_USERNAME_ACTION,
    VERIFYING_USERNAME,
    CONFIRMING_ORDER,
    PROCESSING_PAYMENT
)
from src.payments.order import OrderManager
from src.payments.suffix_manager import SuffixManager
from src.premium.delivery import PremiumDeliveryService
from src.models import OrderType


@pytest.fixture
def mock_bot():
    """创建模拟Bot"""
    bot = AsyncMock()
    bot.send_gift = AsyncMock()
    bot.get_star_transactions = AsyncMock(return_value=[])
    return bot


@pytest.fixture
def mock_order_manager():
    """创建模拟订单管理器"""
    manager = AsyncMock(spec=OrderManager)
    order = MagicMock()
    order.order_id = str(uuid.uuid4())
    order.total_amount = 16.123
    order.unique_suffix = 123
    manager.create_order = AsyncMock(return_value=order)
    manager.cancel_order = AsyncMock()
    return manager


@pytest.fixture
def mock_suffix_manager():
    """创建模拟后缀管理器"""
    manager = AsyncMock(spec=SuffixManager)
    manager.get_suffix = AsyncMock(return_value=123)
    return manager


@pytest.fixture  
def mock_delivery_service(mock_bot, mock_order_manager):
    """创建模拟交付服务"""
    return PremiumDeliveryService(mock_bot, mock_order_manager)


@pytest.fixture
def premium_handler(mock_order_manager, mock_suffix_manager, mock_delivery_service):
    """创建Premium处理器"""
    return PremiumHandlerV2(
        order_manager=mock_order_manager,
        suffix_manager=mock_suffix_manager,
        delivery_service=mock_delivery_service,
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
    update.message = None
    update.callback_query = callback_query
    
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
class TestPremiumSelfPurchase:
    """测试给自己开通Premium"""
    
    async def test_start_premium_command(self, premium_handler, mock_update, mock_context):
        """测试开始Premium购买流程"""
        mock_update.callback_query = None
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        result = await premium_handler.start_premium(mock_update, mock_context)
        
        # 验证返回状态
        assert result == SELECTING_TARGET
        
        # 验证消息发送
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Premium 会员开通" in call_args[0][0]
        assert "给自己开通" in call_args[0][0]
        assert "给他人开通" in call_args[0][0]
    
    async def test_select_self_success(self, premium_handler, mock_update, mock_context):
        """测试选择给自己开通 - 成功场景"""
        mock_update.callback_query.data = "premium_self"
        
        # 执行操作
        result = await premium_handler.select_self(mock_update, mock_context)
        
        # 验证返回状态
        assert result == SELECTING_PACKAGE
        
        # 验证用户数据设置
        assert mock_context.user_data['recipient_type'] == 'self'
        assert mock_context.user_data['recipient_id'] == 123456
        assert mock_context.user_data['recipient_username'] == "testuser"
        assert mock_context.user_data['recipient_nickname'] == "Test"
        
        # 验证消息更新
        mock_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update.callback_query.edit_message_text.call_args
        message_text = call_args[0][0]
        
        assert "为自己开通 Premium" in message_text
        assert "@testuser" in message_text
        assert "请选择套餐时长" in message_text
    
    async def test_select_self_with_error(self, premium_handler, mock_update, mock_context):
        """测试选择给自己开通 - 错误场景"""
        # 记录调用
        call_count = 0
        original_method = Mock()
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            original_method(*args, **kwargs)
            if call_count == 1:
                # 第一次调用（正常业务）抛出异常
                raise Exception("Test error")
            # 第二次调用（显示错误）成功
            return None
        
        mock_update.callback_query.edit_message_text = AsyncMock(side_effect=side_effect)
        
        # 执行操作
        result = await premium_handler.select_self(mock_update, mock_context)
        
        # 验证返回结束状态
        assert result == ConversationHandler.END
        
        # 验证调用了两次edit_message_text
        assert mock_update.callback_query.edit_message_text.call_count == 2
        
        # 验证第二次调用包含错误消息
        calls = original_method.call_args_list
        if len(calls) >= 2:
            error_call = calls[1]
            assert "处理请求时出现错误" in error_call[0][0]
            assert "Test error" in error_call[0][0]
    
    @patch('src.premium.handler_v2.get_db')
    @patch('src.premium.handler_v2.close_db')
    async def test_package_selected_for_self(
        self, 
        mock_close_db, 
        mock_get_db, 
        premium_handler, 
        mock_update, 
        mock_context,
        mock_order_manager
    ):
        """测试选择套餐（给自己）"""
        # 设置数据库模拟
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # 设置上下文数据
        mock_context.user_data = {
            'recipient_type': 'self',
            'recipient_id': 123456,
            'recipient_username': 'testuser',
            'recipient_nickname': 'Test'
        }
        
        # 设置回调数据
        mock_update.callback_query.data = "premium_3"
        
        # 执行操作
        result = await premium_handler.package_selected(mock_update, mock_context)
        
        # 验证返回状态
        assert result == CONFIRMING_ORDER
        
        # 验证订单创建
        assert mock_context.user_data['premium_months'] == 3
        assert mock_context.user_data['base_amount'] == 16.0
        assert 'order_id' in mock_context.user_data
        
        # 验证消息更新
        mock_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update.callback_query.edit_message_text.call_args
        message_text = call_args[0][0]
        
        assert "订单确认" in message_text
        assert "接收账号：您自己" in message_text
        assert "16.123" in message_text  # 包含后缀的金额


@pytest.mark.asyncio
class TestPremiumGiftPurchase:
    """测试给他人开通Premium"""
    
    async def test_select_other_success(self, premium_handler, mock_update, mock_context):
        """测试选择给他人开通 - 成功场景"""
        mock_update.callback_query.data = "premium_other"
        
        # 执行操作
        result = await premium_handler.select_other(mock_update, mock_context)
        
        # 验证返回状态
        assert result == ENTERING_USERNAME
        
        # 验证用户数据设置
        assert mock_context.user_data['recipient_type'] == 'other'
        
        # 验证消息更新
        mock_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update.callback_query.edit_message_text.call_args
        message_text = call_args[0][0]
        
        assert "为他人开通 Premium" in message_text
        assert "请输入对方的 Telegram 用户名" in message_text
    
    async def test_select_other_with_error(self, premium_handler, mock_update, mock_context):
        """测试选择给他人开通 - 错误场景"""
        # 记录调用
        call_count = 0
        original_method = Mock()
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            original_method(*args, **kwargs)
            if call_count == 1:
                # 第一次调用（正常业务）抛出异常
                raise Exception("Network error")
            # 第二次调用（显示错误）成功
            return None
        
        mock_update.callback_query.edit_message_text = AsyncMock(side_effect=side_effect)
        
        # 执行操作
        result = await premium_handler.select_other(mock_update, mock_context)
        
        # 验证返回结束状态
        assert result == ConversationHandler.END
        
        # 验证调用了两次edit_message_text
        assert mock_update.callback_query.edit_message_text.call_count == 2
        
        # 验证第二次调用包含错误消息
        calls = original_method.call_args_list
        if len(calls) >= 2:
            error_call = calls[1]
            assert "处理请求时出现错误" in error_call[0][0]
            assert "Network error" in error_call[0][0]
    
    @patch('src.premium.handler_v2.RecipientParser')
    async def test_username_entered_valid(
        self, 
        mock_parser, 
        premium_handler, 
        mock_update, 
        mock_context
    ):
        """测试输入有效用户名"""
        # 设置模拟
        mock_parser.validate_username.return_value = True
        mock_update.callback_query = None
        mock_update.message = MagicMock()
        mock_update.message.text = "@alice"
        mock_update.message.reply_text = AsyncMock()
        
        # 模拟验证服务
        with patch.object(premium_handler.verification_service, 'verify_user_exists') as mock_verify:
            mock_verify.return_value = {
                'exists': True,
                'is_verified': True,
                'user_id': 654321,
                'nickname': 'Alice',
                'binding_url': 'https://t.me/test_bot?start=bind_alice'
            }
            
            # 执行操作
            result = await premium_handler.username_entered(mock_update, mock_context)
            
            # 验证返回状态
            assert result == VERIFYING_USERNAME
            
            # 验证用户数据
            assert mock_context.user_data['recipient_username'] == 'alice'
            assert mock_context.user_data['recipient_id'] == 654321
            assert mock_context.user_data['recipient_nickname'] == 'Alice'
            
            # 验证消息发送
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            message_text = call_args[0][0]
            assert "找到用户" in message_text
            assert "@alice" in message_text


class TestPremiumConversationHandler:
    """测试Premium对话处理器"""
    
    def test_conversation_handler_creation(self, premium_handler):
        """测试对话处理器创建"""
        handler = premium_handler.get_conversation_handler()
        
        # 验证处理器类型
        assert isinstance(handler, ConversationHandler)
        
        # 验证入口点
        assert len(handler.entry_points) > 0
        
        # 验证状态
        assert SELECTING_TARGET in handler.states
        assert SELECTING_PACKAGE in handler.states
        assert ENTERING_USERNAME in handler.states
        assert VERIFYING_USERNAME in handler.states
        assert CONFIRMING_ORDER in handler.states
        
        # 验证回退处理
        assert len(handler.fallbacks) > 0


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
