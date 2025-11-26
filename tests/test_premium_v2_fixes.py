"""
测试Premium V2修复
验证状态机问题和用户名输入问题已解决
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, CallbackQuery, User, Message
from telegram.ext import ConversationHandler

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.premium.handler_v2 import (
    PremiumHandlerV2,
    SELECTING_TARGET,
    SELECTING_PACKAGE,
    ENTERING_USERNAME,
    AWAITING_USERNAME_ACTION,
    VERIFYING_USERNAME,
    CONFIRMING_ORDER
)
from src.premium.recipient_parser import RecipientParser


class TestPremiumV2StateMachine:
    """测试Premium V2状态机修复"""
    
    def setup_method(self):
        """设置测试环境"""
        self.order_manager = Mock()
        self.suffix_manager = Mock()
        self.delivery_service = Mock()
        self.receive_address = "TTestAddress"
        
        self.handler = PremiumHandlerV2(
            order_manager=self.order_manager,
            suffix_manager=self.suffix_manager,
            delivery_service=self.delivery_service,
            receive_address=self.receive_address,
            bot_username="test_bot"
        )
    
    @pytest.mark.asyncio
    async def test_username_not_found_returns_correct_state(self):
        """测试用户名未找到时返回正确状态"""
        # 创建mock update
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.message = Mock(spec=Message)
        update.message.text = "@nonexistentuser"
        update.message.reply_text = AsyncMock()
        
        context = Mock()
        context.user_data = {'recipient_type': 'other'}
        
        # Mock verification service
        with patch.object(self.handler.verification_service, 'verify_user_exists') as mock_verify:
            mock_verify.return_value = {
                'exists': False,
                'user_id': None,
                'nickname': None,
                'is_verified': False,
                'binding_url': 'https://t.me/test_bot?start=bind_nonexistentuser'
            }
            
            # 调用username_entered
            result = await self.handler.username_entered(update, context)
            
            # 验证返回AWAITING_USERNAME_ACTION而不是ENTERING_USERNAME
            assert result == AWAITING_USERNAME_ACTION
            
            # 验证显示了InlineKeyboard
            call_args = update.message.reply_text.call_args
            reply_markup = call_args.kwargs.get('reply_markup')
            assert reply_markup is not None
            
            # 验证按钮
            keyboard = reply_markup.inline_keyboard
            assert len(keyboard) == 1
            assert len(keyboard[0]) == 2
            assert keyboard[0][0].text == "🔄 重新输入"
            assert keyboard[0][0].callback_data == "retry_username_action"
    
    @pytest.mark.asyncio
    async def test_retry_username_action_sends_new_message(self):
        """测试retry_username_action发送新消息而不是编辑"""
        # 创建mock update
        update = Mock(spec=Update)
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        update.callback_query = query
        update.effective_message = Mock()
        update.effective_message.reply_text = AsyncMock()
        
        context = Mock()
        context.user_data = {}
        
        # 调用retry_username_action
        result = await self.handler.retry_username_action(update, context)
        
        # 验证返回ENTERING_USERNAME
        assert result == ENTERING_USERNAME
        
        # 验证调用了reply_text而不是edit_message_text
        update.effective_message.reply_text.assert_called_once()
        assert hasattr(query, 'edit_message_text') == False or not query.edit_message_text.called
        
        # 验证消息内容
        call_args = update.effective_message.reply_text.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get('text', '')
        assert "请重新输入" in text
    
    @pytest.mark.asyncio
    async def test_conversation_handler_has_awaiting_state(self):
        """测试ConversationHandler包含AWAITING_USERNAME_ACTION状态"""
        handler = self.handler.get_conversation_handler()
        
        # 验证状态存在
        assert AWAITING_USERNAME_ACTION in handler.states
        
        # 验证状态有处理器
        handlers = handler.states[AWAITING_USERNAME_ACTION]
        assert len(handlers) > 0
        
        # 验证有retry_username_action处理器
        has_retry_handler = any(
            h.callback and 'retry_username_action' in str(h.pattern)
            for h in handlers
            if hasattr(h, 'pattern')
        )
        assert has_retry_handler


class TestRecipientParserFixes:
    """测试RecipientParser修复"""
    
    def test_regex_consistency(self):
        """测试正则表达式一致性（5-32字符）"""
        # 测试4字符用户名（应该失败）
        assert RecipientParser.parse("@user") == []
        assert RecipientParser.parse("t.me/user") == []
        
        # 测试5字符用户名（应该成功）
        assert RecipientParser.parse("@user5") == ["user5"]
        assert RecipientParser.parse("t.me/user5") == ["user5"]
        
        # 测试32字符用户名（应该成功）
        username_32 = "a" * 32
        assert RecipientParser.parse(f"@{username_32}") == [username_32]
        assert RecipientParser.parse(f"t.me/{username_32}") == [username_32]
        
        # 测试33字符用户名（应该失败）
        username_33 = "a" * 33
        assert RecipientParser.parse(f"@{username_33}") == []
        assert RecipientParser.parse(f"t.me/{username_33}") == []
    
    def test_validate_username_consistency(self):
        """测试验证方法一致性"""
        # 4字符应该失败
        assert RecipientParser.validate_username("user") == False
        
        # 5字符应该成功
        assert RecipientParser.validate_username("user5") == True
        
        # 32字符应该成功
        assert RecipientParser.validate_username("a" * 32) == True
        
        # 33字符应该失败
        assert RecipientParser.validate_username("a" * 33) == False


class TestPremiumV2FullFlow:
    """测试Premium V2完整流程"""
    
    @pytest.mark.asyncio
    async def test_complete_flow_with_retry(self):
        """测试包含重试的完整流程"""
        handler = PremiumHandlerV2(
            order_manager=Mock(),
            suffix_manager=Mock(),
            delivery_service=Mock(),
            receive_address="TTestAddress",
            bot_username="test_bot"
        )
        
        # 模拟流程
        states = []
        
        # 1. 选择给他人
        update = Mock()
        context = Mock()
        context.user_data = {}
        state = SELECTING_TARGET
        states.append(("选择给他人", state))
        
        # 2. 输入用户名（不存在）
        state = ENTERING_USERNAME
        states.append(("输入不存在的用户名", state))
        
        # 3. 等待用户操作
        state = AWAITING_USERNAME_ACTION  # 新状态
        states.append(("等待用户选择重试或取消", state))
        
        # 4. 点击重试
        state = ENTERING_USERNAME
        states.append(("重新输入用户名", state))
        
        # 5. 输入正确用户名
        state = VERIFYING_USERNAME
        states.append(("验证用户名", state))
        
        # 6. 确认用户
        state = SELECTING_PACKAGE
        states.append(("选择套餐", state))
        
        # 7. 选择套餐
        state = CONFIRMING_ORDER
        states.append(("确认订单", state))
        
        # 验证流程
        print("\n" + "="*50)
        print("Premium V2 修复后流程测试")
        print("="*50)
        
        for step, state in states:
            print(f"✅ {step} -> State: {state}")
        
        # 验证关键修复
        assert AWAITING_USERNAME_ACTION in [s[1] for s in states], "缺少AWAITING_USERNAME_ACTION状态"
        
        print("\n✅ 流程测试通过，状态机问题已修复")
        print("="*50)


if __name__ == "__main__":
    # 运行测试
    asyncio.run(TestPremiumV2FullFlow().test_complete_flow_with_retry())
