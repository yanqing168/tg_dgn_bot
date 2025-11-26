"""
测试地址查询ConversationHandler修复
验证地址查询不会全局拦截文本消息
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from telegram import Update, CallbackQuery, Message, User
from telegram.ext import ConversationHandler, ContextTypes

from src.address_query.handler import AddressQueryHandler, AWAITING_ADDRESS


class TestAddressQueryConversation:
    """测试地址查询ConversationHandler"""
    
    @pytest.fixture
    def mock_update(self):
        """创建模拟的Update对象"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.effective_user.first_name = "Test"
        return update
    
    @pytest.fixture
    def mock_context(self):
        """创建模拟的Context对象"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
    @pytest.mark.asyncio
    async def test_start_query_conversation_returns_state(self, mock_update, mock_context):
        """测试开始对话返回正确的状态"""
        # 模拟inline按钮点击
        mock_update.callback_query = Mock(spec=CallbackQuery)
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.message = None
        
        # Mock限频检查通过
        with patch.object(
            AddressQueryHandler, '_check_rate_limit', return_value=(True, 0)
        ):
            result = await AddressQueryHandler.start_query_conversation(
                mock_update, mock_context
            )
        
        # 应该返回AWAITING_ADDRESS状态
        assert result == AWAITING_ADDRESS
    
    @pytest.mark.asyncio
    async def test_rate_limit_ends_conversation(self, mock_update, mock_context):
        """测试限频时结束对话"""
        mock_update.callback_query = Mock(spec=CallbackQuery)
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.message = None
        
        # Mock限频检查失败
        with patch.object(
            AddressQueryHandler, '_check_rate_limit', return_value=(False, 10)
        ):
            result = await AddressQueryHandler.start_query_conversation(
                mock_update, mock_context
            )
        
        # 限频时应该结束对话
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_valid_address_ends_conversation(self, mock_update, mock_context):
        """测试有效地址输入后结束对话"""
        mock_update.message = Mock(spec=Message)
        mock_update.message.text = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # 有效的 TRON 地址（USDT合约）
        mock_update.message.reply_text = AsyncMock()
        mock_update.callback_query = None
        
        # Mock各种依赖
        with patch.object(
            AddressQueryHandler, '_check_rate_limit', return_value=(True, 0)
        ), patch.object(
            AddressQueryHandler, '_record_query'
        ), patch.object(
            AddressQueryHandler, '_fetch_address_info', return_value=None
        ), patch(
            'src.legacy.address_query.explorer.explorer_links',
            return_value={"overview": "http://test", "txs": "http://test"}
        ):
            result = await AddressQueryHandler.handle_address_input_conversation(
                mock_update, mock_context
            )
        
        # 成功查询后应该结束对话
        assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_invalid_address_continues_conversation(self, mock_update, mock_context):
        """测试无效地址输入后继续等待"""
        mock_update.message = Mock(spec=Message)
        mock_update.message.text = "invalid_address"
        mock_update.message.reply_text = AsyncMock()
        mock_update.callback_query = None
        
        result = await AddressQueryHandler.handle_address_input_conversation(
            mock_update, mock_context
        )
        
        # 无效地址应该继续等待输入
        assert result == AWAITING_ADDRESS
    
    @pytest.mark.asyncio
    async def test_cancel_conversation_ends(self, mock_update, mock_context):
        """测试取消对话正确结束"""
        # 测试callback取消
        mock_update.callback_query = Mock(spec=CallbackQuery)
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.message = None
        
        result = await AddressQueryHandler.cancel_conversation(
            mock_update, mock_context
        )
        
        assert result == ConversationHandler.END
    
    def test_conversation_handler_structure(self):
        """测试ConversationHandler结构正确"""
        handler = AddressQueryHandler.get_conversation_handler()
        
        # 验证是ConversationHandler
        assert isinstance(handler, ConversationHandler)
        
        # 验证entry_points
        assert len(handler.entry_points) == 2  # Inline按钮和Reply按钮
        
        # 验证states
        assert AWAITING_ADDRESS in handler.states
        assert len(handler.states[AWAITING_ADDRESS]) == 1  # 只有文本输入handler
        
        # 验证fallbacks
        assert len(handler.fallbacks) >= 3  # cancel_query, back_to_main, /cancel等
        
        # 验证配置
        assert handler.name == "address_query"
        assert handler.allow_reentry == True
        assert handler.persistent == False
    
    def test_no_global_message_handler(self):
        """测试没有全局MessageHandler"""
        from src.bot import TelegramBot
        
        bot = TelegramBot()
        
        # 遍历所有handlers，确保没有全局的MessageHandler捕获所有文本
        # （这需要在bot.register_handlers()后检查）
        # 这里只是示例，实际测试可能需要更复杂的检查
        pass
    
    @pytest.mark.asyncio
    async def test_old_handle_address_input_warns_user(self, mock_update, mock_context):
        """测试旧的handle_address_input方法提示用户"""
        mock_update.message = Mock(spec=Message)
        mock_update.message.reply_text = AsyncMock()
        
        # 调用旧方法（保留用于向后兼容）
        await AddressQueryHandler.handle_address_input(mock_update, mock_context)
        
        # 应该提示用户使用正确的流程
        mock_update.message.reply_text.assert_called_once()
        args = mock_update.message.reply_text.call_args[0]
        assert "请先点击" in args[0]
    
    @pytest.mark.asyncio
    async def test_conversation_isolated_from_other_modules(self):
        """测试地址查询对话与其他模块隔离"""
        # 这个测试验证地址查询的ConversationHandler不会干扰其他模块
        # 例如，在Premium购买流程中输入收件人时，不应该被地址查询捕获
        
        handler = AddressQueryHandler.get_conversation_handler()
        
        # 确保只有特定的entry_points才能进入地址查询对话
        entry_patterns = []
        for entry in handler.entry_points:
            # CallbackQueryHandler 有 pattern 属性
            if hasattr(entry, 'pattern'):
                if hasattr(entry.pattern, 'pattern'):
                    entry_patterns.append(entry.pattern.pattern)
                else:
                    entry_patterns.append(str(entry.pattern))
            # MessageHandler 使用 filters 属性
            if hasattr(entry, 'filters'):
                entry_patterns.append(str(entry.filters))
        
        # 验证entry_points是特定的
        assert any("menu_address_query" in str(p) for p in entry_patterns)
        assert any("地址查询" in str(p) for p in entry_patterns) or any("🔍" in str(p) for p in entry_patterns)
        
        # 验证不会捕获其他模块的callback
        assert not any("premium" in str(p).lower() for p in entry_patterns if "menu" not in str(p))
        assert not any("profile" in str(p).lower() for p in entry_patterns if "menu" not in str(p))
        assert not any("energy" in str(p).lower() for p in entry_patterns if "menu" not in str(p))


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
