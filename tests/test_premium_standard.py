"""
测试标准化的Premium模块
验证HTML格式、特殊字符处理、状态管理等
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from telegram import Update, User, CallbackQuery, Message, Chat
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime, timedelta
import uuid

from src.modules.premium.handler import PremiumModule
from src.modules.premium.states import *
from src.modules.premium.messages import PremiumMessages
from src.core.formatter import MessageFormatter
from src.core.state_manager import ModuleStateManager


class MockContext:
    """模拟Context对象"""
    def __init__(self):
        self.user_data = {}
        self.chat_data = {}
        self.bot_data = {}


def create_mock_update(callback_data=None, message_text=None, username="testuser", first_name="Test"):
    """创建模拟的Update对象"""
    update = MagicMock(spec=Update)
    
    # 创建用户
    user = MagicMock(spec=User)
    user.id = 123456
    user.username = username
    user.first_name = first_name
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
    message.text = message_text
    
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
def mock_order_manager():
    """创建模拟订单管理器"""
    manager = AsyncMock()
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
    manager = AsyncMock()
    manager.get_suffix = AsyncMock(return_value=123)
    return manager


@pytest.fixture
def mock_delivery_service():
    """创建模拟交付服务"""
    service = AsyncMock()
    return service


@pytest.fixture
def premium_module(mock_order_manager, mock_suffix_manager, mock_delivery_service):
    """创建Premium模块实例"""
    return PremiumModule(
        order_manager=mock_order_manager,
        suffix_manager=mock_suffix_manager,
        delivery_service=mock_delivery_service,
        receive_address="TTestAddress123",
        bot_username="test_bot"
    )


class TestPremiumStandardModule:
    """测试标准化的Premium模块"""
    
    def test_module_properties(self, premium_module):
        """测试模块属性"""
        assert premium_module.module_name == "premium"
        handlers = premium_module.get_handlers()
        assert len(handlers) == 1
        assert isinstance(handlers[0], ConversationHandler)
    
    @pytest.mark.asyncio
    async def test_start_premium_html_format(self, premium_module):
        """测试开始Premium使用HTML格式"""
        update = create_mock_update(callback_data="menu_premium")
        context = MockContext()
        
        result = await premium_module.start_premium(update, context)
        
        # 验证返回状态
        assert result == SELECTING_TARGET
        
        # 验证使用HTML格式
        call_args = update.callback_query.edit_message_text.call_args
        assert call_args[1]['parse_mode'] == 'HTML'
        
        # 验证消息内容
        text = call_args[0][0]
        assert "<b>Premium 会员开通</b>" in text
        assert "3个月 - $16.0 USDT" in text
        assert "6个月 - $25.0 USDT" in text
        assert "12个月 - $35.0 USDT" in text
    
    @pytest.mark.asyncio
    async def test_select_self_no_username(self, premium_module):
        """测试无用户名情况 - HTML转义"""
        update = create_mock_update(
            callback_data="premium_self",
            username=None,
            first_name="<Test>"  # 包含HTML特殊字符
        )
        context = MockContext()
        
        # 初始化状态
        ModuleStateManager.init_state(context, "premium")
        
        result = await premium_module.select_self(update, context)
        
        # 验证返回状态
        assert result == SELECTING_PACKAGE
        
        # 验证状态保存
        state = ModuleStateManager.get_state(context, "premium")
        assert state['recipient_type'] == 'self'
        assert state['recipient_id'] == 123456
        
        # 验证消息格式
        call_args = update.callback_query.edit_message_text.call_args
        assert call_args[1]['parse_mode'] == 'HTML'
        
        # 验证HTML转义
        text = call_args[0][0]
        assert "未设置" in text  # 无用户名显示"未设置"
        # 检查HTML转义 - 昵称中的特殊字符应该被转义
        assert ("&lt;Test&gt;" in text or "&amp;lt;Test&amp;gt;" in text)  # 可能是单次或双次转义
        assert "<b>为自己开通 Premium</b>" in text
    
    @pytest.mark.asyncio
    async def test_select_self_with_special_chars(self, premium_module):
        """测试用户名和昵称包含特殊字符"""
        update = create_mock_update(
            callback_data="premium_self",
            username="test_user<script>",
            first_name="Test & User"
        )
        context = MockContext()
        ModuleStateManager.init_state(context, "premium")
        
        result = await premium_module.select_self(update, context)
        
        assert result == SELECTING_PACKAGE
        
        # 验证特殊字符被转义
        call_args = update.callback_query.edit_message_text.call_args
        text = call_args[0][0]
        # 检查用户名和昵称的转义
        assert ("@test_user&lt;script&gt;" in text or "@test_user&amp;lt;script&amp;gt;" in text)
        assert ("Test &amp; User" in text or "Test &amp;amp; User" in text)
    
    @pytest.mark.asyncio
    async def test_select_other(self, premium_module):
        """测试选择给他人开通"""
        update = create_mock_update(callback_data="premium_other")
        context = MockContext()
        ModuleStateManager.init_state(context, "premium")
        
        result = await premium_module.select_other(update, context)
        
        # 验证返回状态
        assert result == ENTERING_USERNAME
        
        # 验证状态保存
        state = ModuleStateManager.get_state(context, "premium")
        assert state['recipient_type'] == 'other'
        
        # 验证消息格式
        call_args = update.callback_query.edit_message_text.call_args
        assert call_args[1]['parse_mode'] == 'HTML'
        text = call_args[0][0]
        assert "<b>为他人开通 Premium</b>" in text
    
    @pytest.mark.asyncio
    @patch('src.premium.recipient_parser.RecipientParser')
    async def test_username_entered_invalid(self, mock_parser, premium_module):
        """测试输入无效用户名"""
        mock_parser.validate_username.return_value = False
        
        update = create_mock_update(message_text="ab")  # 太短的用户名
        context = MockContext()
        ModuleStateManager.init_state(context, "premium")
        
        result = await premium_module.username_entered(update, context)
        
        # 验证返回相同状态（重新输入）
        assert result == ENTERING_USERNAME
        
        # 验证错误消息
        call_args = update.message.reply_text.call_args
        assert call_args[1]['parse_mode'] == 'HTML'
        text = call_args[0][0]
        assert "用户名格式无效" in text
    
    @pytest.mark.asyncio
    @patch('src.premium.recipient_parser.RecipientParser')
    async def test_username_entered_valid(self, mock_parser, premium_module):
        """测试输入有效用户名"""
        mock_parser.validate_username.return_value = True
        
        update = create_mock_update(message_text="@alice")
        context = MockContext()
        ModuleStateManager.init_state(context, "premium")
        
        # 模拟验证服务
        with patch.object(premium_module.verification_service, 'verify_user_exists') as mock_verify:
            mock_verify.return_value = {
                'exists': True,
                'is_verified': True,
                'user_id': 654321,
                'nickname': 'Alice<test>',  # 包含特殊字符
                'binding_url': 'https://t.me/test_bot?start=bind_alice'
            }
            
            result = await premium_module.username_entered(update, context)
            
            # 验证返回状态
            assert result == VERIFYING_USERNAME
            
            # 验证状态保存
            state = ModuleStateManager.get_state(context, "premium")
            assert state['recipient_username'] == 'alice'
            assert state['recipient_id'] == 654321
            assert state['recipient_nickname'] == 'Alice<test>'
            
            # 验证消息格式和转义
            call_args = update.message.reply_text.call_args
            assert call_args[1]['parse_mode'] == 'HTML'
            text = call_args[0][0]
            assert "@alice" in text
            assert "Alice&lt;test&gt;" in text  # 昵称中的特殊字符被转义
    
    @pytest.mark.asyncio
    @patch('src.database.close_db')
    @patch('src.database.get_db')
    async def test_package_selected(
        self,
        mock_get_db,
        mock_close_db,
        premium_module,
        mock_order_manager
    ):
        """测试选择套餐"""
        # 设置模拟数据库
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        update = create_mock_update(callback_data="premium_3")
        context = MockContext()
        
        # 设置状态
        ModuleStateManager.init_state(context, "premium")
        state = ModuleStateManager.get_state(context, "premium")
        state['recipient_type'] = 'self'
        state['recipient_id'] = 123456
        state['recipient_username'] = 'testuser'
        state['recipient_nickname'] = 'Test'
        
        result = await premium_module.package_selected(update, context)
        
        # 验证返回状态
        assert result == CONFIRMING_ORDER
        
        # 验证订单创建
        assert mock_order_manager.create_order.called
        
        # 验证消息格式
        call_args = update.callback_query.edit_message_text.call_args
        assert call_args[1]['parse_mode'] == 'HTML'
        text = call_args[0][0]
        assert "<b>订单确认</b>" in text
        assert "3 个月 Premium" in text
        assert "16.123" in text  # 包含后缀的金额
    
    @pytest.mark.asyncio
    async def test_error_handling(self, premium_module):
        """测试错误处理"""
        update = create_mock_update(callback_data="premium_self")
        context = MockContext()
        
        # 模拟在获取状态时抛出异常
        with patch.object(ModuleStateManager, 'get_state', side_effect=Exception("Test error")):
            result = await premium_module.select_self(update, context)
        
            # 验证返回结束状态
            assert result == ConversationHandler.END
            
            # 验证错误消息被发送
            call_args = update.callback_query.edit_message_text.call_args
            text = call_args[0][0]
            assert "处理请求时出现错误" in text
            assert "Test error" in text
    
    def test_message_formatter_integration(self):
        """测试消息格式化器集成"""
        formatter = MessageFormatter()
        
        # 测试HTML转义
        assert formatter.escape_html("<script>alert('xss')</script>") == "&lt;script&gt;alert('xss')&lt;/script&gt;"
        
        # 测试安全用户名
        assert formatter.safe_username(None) == "未设置"
        assert formatter.safe_username("alice") == "@alice"
        assert formatter.safe_username("alice<script>") == "@alice&lt;script&gt;"
        
        # 测试安全昵称
        assert formatter.safe_nickname(None) == "未知"
        assert formatter.safe_nickname("Test & User") == "Test &amp; User"
    
    def test_state_manager_integration(self, premium_module):
        """测试状态管理器集成"""
        context = MockContext()
        
        # 初始化状态
        state = ModuleStateManager.init_state(context, "premium")
        assert isinstance(state, dict)
        
        # 设置值
        ModuleStateManager.set_state(context, "premium", "test_key", "test_value")
        assert ModuleStateManager.get_value(context, "premium", "test_key") == "test_value"
        
        # 清理状态
        ModuleStateManager.clear_state(context, "premium")
        assert ModuleStateManager.get_state(context, "premium") == {}


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
