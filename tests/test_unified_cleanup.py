"""
测试统一用户数据清理机制
验证所有模块使用NavigationManager.cleanup_and_show_main_menu
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from telegram import Update, User, CallbackQuery, Message, Chat
from telegram.ext import ContextTypes, ConversationHandler

from src.common.navigation_manager import NavigationManager


@pytest.fixture
def mock_update():
    """创建模拟Update对象"""
    update = MagicMock(spec=Update)
    
    user = MagicMock(spec=User)
    user.id = 123456
    user.username = "testuser"
    user.first_name = "Test"
    
    query = MagicMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.message = MagicMock()
    
    update.effective_user = user
    update.callback_query = query
    update.message = None
    
    return update


@pytest.fixture
def mock_context():
    """创建模拟Context对象"""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {
        'user_id': 123456,
        'username': 'testuser',
        'main_menu_keyboard_shown': True,
        'premium_order_id': 'test-order-123',
        'energy_type': 'hourly',
        'temp_data': 'should_be_cleared'
    }
    context.chat_data = {}
    return context


class TestUnifiedCleanup:
    """测试统一清理机制"""
    
    @pytest.mark.asyncio
    async def test_cleanup_and_show_main_menu_exists(self):
        """测试cleanup_and_show_main_menu方法存在"""
        assert hasattr(NavigationManager, 'cleanup_and_show_main_menu')
        assert callable(NavigationManager.cleanup_and_show_main_menu)
    
    @pytest.mark.asyncio
    async def test_cleanup_and_show_main_menu_preserves_important_data(
        self, mock_update, mock_context
    ):
        """测试清理时保留重要数据"""
        with patch.object(NavigationManager, '_show_main_menu', new=AsyncMock()):
            result = await NavigationManager.cleanup_and_show_main_menu(
                mock_update, mock_context
            )
        
        # 验证返回值
        assert result == ConversationHandler.END
        
        # 验证保留的数据
        assert 'user_id' in mock_context.user_data
        assert 'username' in mock_context.user_data
        assert 'main_menu_keyboard_shown' in mock_context.user_data
        assert mock_context.user_data['main_menu_keyboard_shown'] == True
        
        # 验证临时数据被清除
        assert 'premium_order_id' not in mock_context.user_data
        assert 'energy_type' not in mock_context.user_data
        assert 'temp_data' not in mock_context.user_data
    
    @pytest.mark.asyncio
    async def test_cleanup_and_show_main_menu_calls_show_main_menu(
        self, mock_update, mock_context
    ):
        """测试清理后调用show_main_menu"""
        with patch.object(NavigationManager, '_show_main_menu', new=AsyncMock()) as mock_show:
            await NavigationManager.cleanup_and_show_main_menu(
                mock_update, mock_context
            )
            
            # 验证调用了show_main_menu
            mock_show.assert_called_once_with(mock_update, mock_context)


class TestModulesCancelMethods:
    """测试各模块的cancel方法使用统一清理"""
    
    @pytest.mark.asyncio
    async def test_premium_cancel_uses_unified_cleanup(self, mock_update, mock_context):
        """测试Premium模块的cancel使用统一清理"""
        from src.premium.handler_v2 import PremiumHandlerV2
        from src.payments.order import OrderManager
        from src.payments.suffix_manager import SuffixManager
        from src.premium.delivery import PremiumDeliveryService
        
        # 创建handler
        bot = AsyncMock()
        order_manager = AsyncMock(spec=OrderManager)
        suffix_manager = AsyncMock(spec=SuffixManager)
        delivery_service = PremiumDeliveryService(bot, order_manager)
        
        handler = PremiumHandlerV2(
            order_manager=order_manager,
            suffix_manager=suffix_manager,
            delivery_service=delivery_service,
            receive_address="TTest123",
            bot_username="test_bot"
        )
        
        # Mock NavigationManager
        with patch.object(NavigationManager, 'cleanup_and_show_main_menu', new=AsyncMock()) as mock_cleanup:
            mock_cleanup.return_value = ConversationHandler.END
            
            result = await handler.cancel(mock_update, mock_context)
            
            # 验证调用了统一清理方法
            mock_cleanup.assert_called_once()
            assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_profile_cancel_uses_unified_cleanup(self, mock_update, mock_context):
        """测试Profile模块的cancel使用统一清理"""
        from src.wallet.profile_handler import ProfileHandler
        
        with patch.object(NavigationManager, 'cleanup_and_show_main_menu', new=AsyncMock()) as mock_cleanup:
            mock_cleanup.return_value = ConversationHandler.END
            
            result = await ProfileHandler.cancel(mock_update, mock_context)
            
            # 验证调用了统一清理方法
            mock_cleanup.assert_called_once()
            assert result == ConversationHandler.END
    
    @pytest.mark.asyncio
    async def test_help_cancel_uses_unified_cleanup(self, mock_update, mock_context):
        """测试Help模块的cancel使用统一清理"""
        from src.help.handler import cancel
        
        with patch.object(NavigationManager, 'cleanup_and_show_main_menu', new=AsyncMock()) as mock_cleanup:
            mock_cleanup.return_value = ConversationHandler.END
            
            result = await cancel(mock_update, mock_context)
            
            # 验证调用了统一清理方法
            mock_cleanup.assert_called_once()
            assert result == ConversationHandler.END


class TestCleanupConsistency:
    """测试清理一致性"""
    
    @pytest.mark.asyncio
    async def test_multiple_modules_preserve_same_keys(self, mock_update):
        """测试多个模块清理后保留相同的键"""
        # 创建多个上下文，模拟不同模块
        contexts = []
        for i in range(3):
            context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
            context.user_data = {
                'user_id': 123456,
                'username': 'testuser',
                'main_menu_keyboard_shown': True,
                f'module_{i}_data': f'data_{i}',
                'temp_data': 'temp'
            }
            contexts.append(context)
        
        # 对每个上下文执行清理
        with patch.object(NavigationManager, '_show_main_menu', new=AsyncMock()):
            for context in contexts:
                await NavigationManager.cleanup_and_show_main_menu(mock_update, context)
        
        # 验证所有上下文保留相同的键
        preserved_keys_list = [set(ctx.user_data.keys()) for ctx in contexts]
        
        # 所有上下文应该有相同的保留键
        assert all(keys == preserved_keys_list[0] for keys in preserved_keys_list)
        
        # 验证保留了重要键
        for context in contexts:
            assert 'user_id' in context.user_data
            assert 'username' in context.user_data
            assert 'main_menu_keyboard_shown' in context.user_data


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
