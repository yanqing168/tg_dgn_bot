"""
测试NavigationManager的PRESERVED_KEYS修复
验证main_menu_keyboard_shown在导航时不被清除
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from telegram import Update, User, CallbackQuery, Message, Chat
from telegram.ext import ContextTypes

from src.common.navigation_manager import NavigationManager


@pytest.fixture
def mock_context():
    """创建模拟Context对象"""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {
        'user_id': 123456,
        'username': 'testuser',
        'first_name': 'Test',
        'is_admin': False,
        'language': 'zh',
        'last_command': '/start',
        'current_module': 'premium',
        'main_menu_keyboard_shown': True,  # 关键：键盘已显示
        'some_temp_data': 'should_be_cleared',  # 临时数据
        'order_id': 'test-123',  # 订单数据
    }
    context.chat_data = {}
    return context


class TestNavigationPreservedKeys:
    """测试PRESERVED_KEYS修复"""
    
    def test_preserved_keys_includes_keyboard_shown(self):
        """测试PRESERVED_KEYS包含main_menu_keyboard_shown"""
        assert 'main_menu_keyboard_shown' in NavigationManager.PRESERVED_KEYS
        assert 'user_id' in NavigationManager.PRESERVED_KEYS
        assert 'username' in NavigationManager.PRESERVED_KEYS
    
    def test_cleanup_preserves_keyboard_shown(self, mock_context):
        """测试清理数据时保留main_menu_keyboard_shown"""
        # 执行清理
        NavigationManager._cleanup_conversation_data(mock_context)
        
        # 验证保留的键
        assert 'main_menu_keyboard_shown' in mock_context.user_data
        assert mock_context.user_data['main_menu_keyboard_shown'] == True
        
        # 验证其他保留键
        assert mock_context.user_data['user_id'] == 123456
        assert mock_context.user_data['username'] == 'testuser'
        assert mock_context.user_data['first_name'] == 'Test'
        
        # 验证临时数据被清除
        assert 'some_temp_data' not in mock_context.user_data
        assert 'order_id' not in mock_context.user_data
    
    def test_cleanup_preserves_all_keys(self, mock_context):
        """测试清理时保留所有PRESERVED_KEYS中的键"""
        NavigationManager._cleanup_conversation_data(mock_context)
        
        for key in NavigationManager.PRESERVED_KEYS:
            if key in ['user_id', 'username', 'first_name', 'is_admin', 
                      'language', 'last_command', 'current_module', 'main_menu_keyboard_shown']:
                assert key in mock_context.user_data, f"键 {key} 应该被保留"
    
    def test_cleanup_removes_non_preserved_keys(self, mock_context):
        """测试清理时删除非保留键"""
        NavigationManager._cleanup_conversation_data(mock_context)
        
        # 这些键不应该存在
        assert 'some_temp_data' not in mock_context.user_data
        assert 'order_id' not in mock_context.user_data
    
    def test_keyboard_shown_false_preserved(self, mock_context):
        """测试main_menu_keyboard_shown为False时也被保留"""
        mock_context.user_data['main_menu_keyboard_shown'] = False
        
        NavigationManager._cleanup_conversation_data(mock_context)
        
        assert 'main_menu_keyboard_shown' in mock_context.user_data
        assert mock_context.user_data['main_menu_keyboard_shown'] == False
    
    def test_keyboard_shown_missing_not_added(self, mock_context):
        """测试如果main_menu_keyboard_shown不存在，清理后也不会添加"""
        # 删除该键
        del mock_context.user_data['main_menu_keyboard_shown']
        
        NavigationManager._cleanup_conversation_data(mock_context)
        
        # 不应该被添加
        assert 'main_menu_keyboard_shown' not in mock_context.user_data


class TestNavigationIntegration:
    """集成测试：验证导航流程中键盘状态保留"""
    
    @pytest.mark.asyncio
    async def test_navigation_preserves_keyboard_state(self, mock_context):
        """测试导航到主菜单时保留键盘状态"""
        # 设置初始状态
        mock_context.user_data['main_menu_keyboard_shown'] = True
        mock_context.user_data['premium_order_id'] = 'test-order'
        
        # 模拟Update
        update = MagicMock(spec=Update)
        user = MagicMock(spec=User)
        user.id = 123456
        user.username = "testuser"
        
        query = MagicMock(spec=CallbackQuery)
        query.data = "back_to_main"
        query.answer = AsyncMock()
        query.message = MagicMock()
        query.message.reply_text = AsyncMock()
        
        update.callback_query = query
        update.effective_user = user
        
        # 模拟show_main_menu
        with patch.object(NavigationManager, '_show_main_menu', new=AsyncMock()):
            # 执行导航
            result = await NavigationManager.handle_navigation(update, mock_context)
        
        # 验证键盘状态被保留
        assert 'main_menu_keyboard_shown' in mock_context.user_data
        assert mock_context.user_data['main_menu_keyboard_shown'] == True
        
        # 验证临时数据被清除
        assert 'premium_order_id' not in mock_context.user_data


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
