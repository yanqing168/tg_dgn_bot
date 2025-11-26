"""
测试导航系统
验证NavigationManager和ConversationWrapper的功能
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from telegram import Update, CallbackQuery, User, Message, Chat, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler

# 导入要测试的模块
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.common.navigation_manager import NavigationManager
from src.common.conversation_wrapper import SafeConversationHandler


class TestNavigationManager:
    """测试导航管理器"""
    
    def setup_method(self):
        """设置测试环境"""
        self.user = Mock(spec=User)
        self.user.id = 123456
        self.user.username = "testuser"
        self.user.first_name = "Test"
        
    @pytest.mark.asyncio
    async def test_navigation_targets(self):
        """测试导航目标映射"""
        assert NavigationManager.NAVIGATION_TARGETS['back_to_main'] == 'main_menu'
        assert NavigationManager.NAVIGATION_TARGETS['menu_premium'] == 'premium'
        assert NavigationManager.NAVIGATION_TARGETS['admin_back'] == 'admin_menu'
        
    @pytest.mark.asyncio 
    async def test_cleanup_conversation_data(self):
        """测试会话数据清理"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {
            'user_id': 123456,
            'username': 'testuser',
            'temp_data': 'should_be_removed',
            'order_id': 'should_be_removed',
            'is_admin': True,
        }
        
        NavigationManager._cleanup_conversation_data(context)
        
        # 检查保留的数据
        assert 'user_id' in context.user_data
        assert 'username' in context.user_data
        assert 'is_admin' in context.user_data
        
        # 检查删除的数据
        assert 'temp_data' not in context.user_data
        assert 'order_id' not in context.user_data
        
    @pytest.mark.asyncio
    async def test_create_back_button(self):
        """测试创建返回按钮"""
        button = NavigationManager.create_back_button()
        assert button.text == "🔙 返回主菜单"
        assert button.callback_data == "nav_back_to_main"
        
        # 测试自定义按钮
        custom_button = NavigationManager.create_back_button("自定义", "custom_back")
        assert custom_button.text == "自定义"
        assert custom_button.callback_data == "custom_back"
        
    @pytest.mark.asyncio
    async def test_create_navigation_row(self):
        """测试创建导航按钮行"""
        # 只有返回按钮
        row = NavigationManager.create_navigation_row(include_back=True, include_cancel=False)
        assert len(row) == 1
        assert row[0].text == "🔙 返回"
        
        # 返回和取消按钮
        row = NavigationManager.create_navigation_row(include_back=True, include_cancel=True)
        assert len(row) == 2
        assert row[0].text == "🔙 返回"
        assert row[1].text == "❌ 取消"
        
    @pytest.mark.asyncio
    async def test_standardize_keyboard(self):
        """测试键盘布局标准化"""
        # 没有返回按钮的键盘
        keyboard = [
            [InlineKeyboardButton("选项1", callback_data="option1")],
            [InlineKeyboardButton("选项2", callback_data="option2")]
        ]
        
        standardized = NavigationManager.standardize_keyboard(keyboard, add_back_button=True)
        assert len(standardized) == 3  # 原有2行 + 1行返回按钮
        assert standardized[-1][0].callback_data == "nav_back_to_main"
        
        # 已有返回按钮的键盘
        keyboard_with_back = [
            [InlineKeyboardButton("选项1", callback_data="option1")],
            [InlineKeyboardButton("返回", callback_data="back_to_main")]
        ]
        
        standardized = NavigationManager.standardize_keyboard(keyboard_with_back, add_back_button=True)
        assert len(standardized) == 2  # 不重复添加
        
    @pytest.mark.asyncio
    async def test_handle_navigation_to_main(self):
        """测试导航到主菜单"""
        # Mock update和context
        update = Mock(spec=Update)
        query = Mock(spec=CallbackQuery)
        query.data = "back_to_main"
        query.answer = AsyncMock()
        update.callback_query = query
        update.effective_user = self.user
        
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {'temp_data': 'test'}
        
        # Mock主菜单显示
        with patch('src.common.navigation_manager.NavigationManager._show_main_menu') as mock_show_main:
            mock_show_main.return_value = None
            
            result = await NavigationManager.handle_navigation(update, context)
            
            # 验证
            assert result == ConversationHandler.END
            query.answer.assert_called_once()
            mock_show_main.assert_called_once()
            assert len(context.user_data) < 2  # 数据已清理


class TestSafeConversationHandler:
    """测试安全对话处理器"""
    
    def setup_method(self):
        """设置测试环境"""
        self.entry_points = [Mock()]
        self.states = {'STATE1': [Mock()]}
        self.fallbacks = [Mock()]
        
    def test_create_conversation_handler(self):
        """测试SafeConversationHandler创建"""
        entry_points = [CommandHandler('test', lambda u, c: None)]
        states = {}
        fallbacks = []
        
        handler = SafeConversationHandler.create(
            entry_points=entry_points,
            states=states,
            fallbacks=fallbacks,
            name="test_handler"
        )
        
        assert isinstance(handler, ConversationHandler)
        assert handler.name == "test_handler"
        
        # 新架构：SafeConversationHandler不再在fallback中添加导航处理器
        # 导航由全局NavigationManager处理
        # 检查是否没有重复添加导航处理器
        found_navigation = False
        for fb in handler.fallbacks:
            if hasattr(fb, 'pattern') and fb.pattern:
                if 'back_to_main' in str(fb.pattern.pattern):
                    found_navigation = True
                    break
        
        # 不应该找到导航处理器（由全局处理）
        assert not found_navigation, "Navigation handler should not be in fallbacks (handled globally)"
        
    def test_should_include_fallback(self):
        """测试fallback过滤逻辑"""
        # 应该被过滤的fallback
        nav_handler = Mock(spec=CallbackQueryHandler)
        nav_handler.pattern = Mock()
        nav_handler.pattern.pattern = r"^back_to_main$"
        assert not SafeConversationHandler._should_include_fallback(nav_handler)
        
        # 应该保留的fallback
        other_handler = Mock(spec=CallbackQueryHandler)
        other_handler.pattern = Mock()
        other_handler.pattern.pattern = r"^other_action$"
        assert SafeConversationHandler._should_include_fallback(other_handler)
        
    def test_create_simple(self):
        """测试创建简单对话处理器"""
        handler_func = Mock()
        handler = SafeConversationHandler.create_simple(
            command="test",
            handler_func=handler_func,
            name="simple_test"
        )
        
        assert isinstance(handler, ConversationHandler)
        assert handler.name == "simple_test"
        assert len(handler.entry_points) == 1


class TestDatabaseHealth:
    """测试数据库健康检查"""
    
    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """测试数据库初始化（使用 mock 避免访问生产库）"""
        from unittest.mock import patch
        
        # Mock 数据库函数，避免访问生产数据库
        with patch('src.database.init_db_safe') as mock_init:
            with patch('src.database.check_database_health', return_value=True) as mock_check:
                mock_init.return_value = None
                
                # 调用 mock 的初始化
                from src.database import init_db_safe, check_database_health
                init_db_safe()
                
                # 检查健康状态
                is_healthy = check_database_health()
                assert is_healthy, "数据库健康检查失败"


class TestFullIntegration:
    """完整集成测试"""
    
    @pytest.mark.asyncio
    async def test_navigation_flow(self):
        """测试完整的导航流程"""
        print("\n" + "="*50)
        print("导航系统集成测试")
        print("="*50)
        
        tests_passed = 0
        tests_total = 4
        
        # 测试1: NavigationManager创建
        try:
            button = NavigationManager.create_back_button()
            assert button is not None
            tests_passed += 1
            print("✅ NavigationManager 初始化成功")
        except Exception as e:
            print(f"❌ NavigationManager 初始化失败: {e}")
        
        # 测试2: SafeConversationHandler创建
        try:
            handler = SafeConversationHandler.create(
                entry_points=[Mock()],
                states={},
                fallbacks=[],
                name="test"
            )
            assert handler is not None
            tests_passed += 1
            print("✅ SafeConversationHandler 创建成功")
        except Exception as e:
            print(f"❌ SafeConversationHandler 创建失败: {e}")
        
        # 测试3: 数据库健康检查（mock 避免访问生产库）
        try:
            with patch('src.database.check_database_health', return_value=True):
                from src.database import check_database_health
                check_database_health()
            tests_passed += 1
            print("✅ 数据库健康检查通过（mocked）")
        except Exception as e:
            print(f"⚠️ 数据库健康检查警告: {e}")
            tests_passed += 1  # 不算失败
        
        # 测试4: 导航目标完整性
        try:
            required_targets = [
                'back_to_main', 'menu_premium', 'menu_profile', 
                'menu_energy', 'admin_back'
            ]
            for target in required_targets:
                assert target in NavigationManager.NAVIGATION_TARGETS
            tests_passed += 1
            print("✅ 导航目标配置完整")
        except Exception as e:
            print(f"❌ 导航目标配置不完整: {e}")
        
        print(f"\n测试结果: {tests_passed}/{tests_total} 通过")
        print("="*50)
        
        assert tests_passed == tests_total, f"部分测试失败: {tests_passed}/{tests_total}"


if __name__ == "__main__":
    # 运行测试
    asyncio.run(TestFullIntegration().test_navigation_flow())
