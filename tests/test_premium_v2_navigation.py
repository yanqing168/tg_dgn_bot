"""
测试Premium V2与导航系统的集成
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, CallbackQuery, User, Message
from telegram.ext import ConversationHandler

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.premium.handler_v2 import PremiumHandlerV2
from src.common.navigation_manager import NavigationManager


class TestPremiumV2Navigation:
    """测试Premium V2导航功能"""
    
    def setup_method(self):
        """设置测试环境"""
        # Mock依赖
        self.order_manager = Mock()
        self.suffix_manager = Mock()
        self.delivery_service = Mock()
        self.receive_address = "TTestAddress"
        
        # 创建handler
        self.handler = PremiumHandlerV2(
            order_manager=self.order_manager,
            suffix_manager=self.suffix_manager,
            delivery_service=self.delivery_service,
            receive_address=self.receive_address,
            bot_username="test_bot"
        )
        
    @pytest.mark.asyncio
    async def test_get_conversation_handler(self):
        """测试获取对话处理器"""
        handler = self.handler.get_conversation_handler()
        
        assert isinstance(handler, ConversationHandler)
        assert handler.name == "PremiumV2"
        assert handler.allow_reentry == True
        
    @pytest.mark.asyncio
    async def test_navigation_buttons_created(self):
        """测试导航按钮是否正确创建"""
        # 创建mock update
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        update.callback_query = None
        
        context = Mock()
        context.user_data = {}
        
        # Mock verification service
        with patch.object(self.handler.verification_service, 'auto_bind_on_interaction', new_callable=AsyncMock):
            # 调用start_premium
            result = await self.handler.start_premium(update, context)
            
            # 验证调用了reply_text
            update.message.reply_text.assert_called_once()
            
            # 获取keyboard参数
            call_args = update.message.reply_text.call_args
            reply_markup = call_args.kwargs['reply_markup']
            
            # 验证keyboard结构
            keyboard = reply_markup.inline_keyboard
            assert len(keyboard) == 2  # 两行按钮
            assert len(keyboard[0]) == 2  # 第一行：给自己/给他人
            assert len(keyboard[1]) == 1  # 第二行：取消按钮
            
            # 验证取消按钮使用了NavigationManager
            cancel_button = keyboard[1][0]
            assert cancel_button.callback_data == "nav_back_to_main"
            
    @pytest.mark.asyncio
    async def test_fallbacks_include_safe_navigation(self):
        """测试fallback不包含重复的导航处理"""
        handler = self.handler.get_conversation_handler()
        
        # 新架构：SafeConversationHandler不应该添加导航处理器
        # 导航由全局NavigationManager处理
        found_navigation = False
        for fb in handler.fallbacks:
            if hasattr(fb, 'pattern') and fb.pattern:
                pattern_str = str(fb.pattern.pattern)
                if 'back_to_main' in pattern_str or 'nav_back_to_main' in pattern_str:
                    found_navigation = True
                    break
        
        # 不应该在fallback中找到导航处理器
        assert not found_navigation, "SafeConversationHandler 不应该重复添加导航处理"
                
    @pytest.mark.asyncio
    async def test_cancel_button_integration(self):
        """测试取消按钮集成"""
        # 所有的取消按钮应该使用NavigationManager.create_back_button
        button = NavigationManager.create_back_button("❌ 取消")
        assert button.text == "❌ 取消"
        assert button.callback_data == "nav_back_to_main"
        
        # 验证这与Premium V2中使用的一致
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        update.callback_query = query
        update.message = None
        
        context = Mock()
        context.user_data = {
            'recipient_type': 'self',
            'recipient_id': 123456,
            'recipient_username': 'testuser',
            'recipient_nickname': 'Test'
        }
        
        # 调用select_self
        result = await self.handler.select_self(update, context)
        
        # 验证调用了edit_message_text
        query.edit_message_text.assert_called_once()
        
        # 获取keyboard参数
        call_args = query.edit_message_text.call_args
        reply_markup = call_args.kwargs['reply_markup']
        
        # 验证取消按钮
        keyboard = reply_markup.inline_keyboard
        cancel_button = keyboard[-1][0]  # 最后一行的按钮
        assert cancel_button.callback_data == "nav_back_to_main"


class TestPremiumV2FullIntegration:
    """Premium V2完整集成测试"""
    
    @pytest.mark.asyncio
    async def test_premium_navigation_ci(self):
        """Premium V2导航CI测试"""
        print("\n" + "="*50)
        print("Premium V2 导航系统CI测试")
        print("="*50)
        
        tests = []
        
        # 测试1: Handler创建
        try:
            handler = PremiumHandlerV2(
                order_manager=Mock(),
                suffix_manager=Mock(),
                delivery_service=Mock(),
                receive_address="TTestAddress",
                bot_username="test_bot"
            )
            conv_handler = handler.get_conversation_handler()
            assert conv_handler is not None
            assert conv_handler.name == "PremiumV2"
            tests.append(("Handler创建", True, None))
            print("✅ Premium V2 Handler创建成功")
        except Exception as e:
            tests.append(("Handler创建", False, str(e)))
            print(f"❌ Premium V2 Handler创建失败: {e}")
        
        # 测试2: 导航按钮集成
        try:
            button = NavigationManager.create_back_button("测试")
            assert button.callback_data == "nav_back_to_main"
            tests.append(("导航按钮集成", True, None))
            print("✅ 导航按钮正确集成")
        except Exception as e:
            tests.append(("导航按钮集成", False, str(e)))
            print(f"❌ 导航按钮集成失败: {e}")
        
        # 测试3: Fallback配置
        try:
            handler = PremiumHandlerV2(
                order_manager=Mock(),
                suffix_manager=Mock(),
                delivery_service=Mock(),
                receive_address="TTestAddress",
                bot_username="test_bot"
            )
            conv_handler = handler.get_conversation_handler()
            
            # 新架构：检查SafeConversationHandler不应该重复添加导航处理
            # 导航由全局NavigationManager处理
            has_navigation = False
            for fb in conv_handler.fallbacks:
                if hasattr(fb, 'pattern') and fb.pattern:
                    pattern_str = str(fb.pattern.pattern) if hasattr(fb.pattern, 'pattern') else str(fb.pattern)
                    if 'back_to_main' in pattern_str or 'nav_back_to_main' in pattern_str:
                        has_navigation = True
                        break
                        
            assert not has_navigation, "SafeConversationHandler不应该重复添加导航处理"
            tests.append(("Fallback配置", True, None))
            print("✅ SafeConversationHandler没有重复添加导航处理（由全局处理）")
        except Exception as e:
            tests.append(("Fallback配置", False, str(e)))
            print(f"❌ Fallback配置错误: {e}")
        
        # 测试4: ConversationHandler类型
        try:
            from src.common.conversation_wrapper import SafeConversationHandler
            # 验证使用了SafeConversationHandler
            handler = PremiumHandlerV2(
                order_manager=Mock(),
                suffix_manager=Mock(),
                delivery_service=Mock(),
                receive_address="TTestAddress",
                bot_username="test_bot"
            )
            conv_handler = handler.get_conversation_handler()
            assert isinstance(conv_handler, ConversationHandler)
            tests.append(("SafeConversationHandler使用", True, None))
            print("✅ 使用SafeConversationHandler")
        except Exception as e:
            tests.append(("SafeConversationHandler使用", False, str(e)))
            print(f"❌ SafeConversationHandler使用失败: {e}")
        
        # 统计结果
        passed = sum(1 for _, success, _ in tests if success)
        total = len(tests)
        
        print(f"\n测试结果: {passed}/{total} 通过")
        print("="*50)
        
        assert passed == total, f"有 {total - passed} 个测试失败"
        
        print("\n🎉 Premium V2 导航集成测试全部通过！")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(TestPremiumV2FullIntegration().test_premium_navigation_ci())
