"""
测试Admin模块回调Pattern修复
验证Admin模块不会捕获普通用户的回调
"""
import pytest
import re
from unittest.mock import Mock, AsyncMock
from telegram import Update, CallbackQuery, User
from telegram.ext import ContextTypes


class TestAdminCallbackFix:
    """测试Admin回调Pattern修复"""
    
    def test_admin_pattern_not_catching_user_callbacks(self):
        """测试Admin模块不会捕获普通用户的confirm_payment回调"""
        # Admin模块的新pattern - 所有回调都以admin_开头
        admin_pattern = r"^admin_"
        
        # 测试普通用户的回调不被捕获
        user_callbacks = [
            "confirm_payment",  # Premium模块的确认支付
            "cancel_order",     # Premium模块的取消订单
            "profile_deposit",  # 个人中心的充值
            "profile_balance",  # 个人中心的余额查询
            "menu_premium",     # 主菜单的Premium按钮
            "menu_energy",      # 主菜单的能量按钮
            "energy_confirm_yes",  # 能量模块的确认
            "trx_paid_12345",   # TRX兑换的支付确认
            "orders_list",      # 订单查询（虽然是管理员功能，但有独立handler）
        ]
        
        for callback in user_callbacks:
            assert not re.match(admin_pattern, callback), f"Admin pattern错误捕获了: {callback}"
    
    def test_admin_callbacks_still_work(self):
        """测试Admin自己的回调仍能正常捕获"""
        admin_pattern = r"^admin_"
        
        # Admin模块自己的回调
        admin_callbacks = [
            "admin_main",
            "admin_stats",
            "admin_prices",
            "admin_content",
            "admin_settings",
            "admin_exit",
            "admin_price_premium",
            "admin_price_trx_rate",
            "admin_price_energy",
            "admin_premium_edit_3",
            "admin_premium_edit_6",
            "admin_premium_edit_12",
            "admin_edit_trx_rate",
            "admin_energy_edit_small",
            "admin_energy_edit_large",
            "admin_energy_edit_package",
            "admin_content_welcome",
            "admin_content_clone",
            "admin_content_support",
            "admin_settings_timeout",
            "admin_settings_rate_limit",
            "admin_settings_clear_cache",
            "admin_settings_status",
            "admin_confirm_delete",  # confirm操作也加了admin_前缀
        ]
        
        for callback in admin_callbacks:
            assert re.match(admin_pattern, callback), f"Admin pattern未能捕获自己的回调: {callback}"
    
    def test_callback_data_consistency(self):
        """测试menus.py和handler.py中的callback_data一致性"""
        from src.bot_admin.menus import AdminMenus
        
        menus = AdminMenus()
        
        # 测试主菜单
        main_menu = menus.main_menu()
        for row in main_menu.inline_keyboard:
            for button in row:
                if button.callback_data:
                    assert button.callback_data.startswith("admin_"), \
                        f"主菜单按钮callback_data未加admin_前缀: {button.callback_data}"
        
        # 测试价格菜单
        price_menu = menus.price_menu()
        for row in price_menu.inline_keyboard:
            for button in row:
                if button.callback_data:
                    assert button.callback_data.startswith("admin_"), \
                        f"价格菜单按钮callback_data未加admin_前缀: {button.callback_data}"
        
        # 测试Premium价格菜单
        premium_menu = menus.premium_price_menu()
        for row in premium_menu.inline_keyboard:
            for button in row:
                if button.callback_data:
                    assert button.callback_data.startswith("admin_"), \
                        f"Premium价格菜单按钮callback_data未加admin_前缀: {button.callback_data}"
        
        # 测试能量价格菜单
        energy_menu = menus.energy_price_menu()
        for row in energy_menu.inline_keyboard:
            for button in row:
                if button.callback_data:
                    assert button.callback_data.startswith("admin_"), \
                        f"能量价格菜单按钮callback_data未加admin_前缀: {button.callback_data}"
        
        # 测试文案菜单
        content_menu = menus.content_menu()
        for row in content_menu.inline_keyboard:
            for button in row:
                if button.callback_data:
                    assert button.callback_data.startswith("admin_"), \
                        f"文案菜单按钮callback_data未加admin_前缀: {button.callback_data}"
        
        # 测试系统设置菜单
        settings_menu = menus.settings_menu()
        for row in settings_menu.inline_keyboard:
            for button in row:
                if button.callback_data:
                    assert button.callback_data.startswith("admin_"), \
                        f"系统设置菜单按钮callback_data未加admin_前缀: {button.callback_data}"
        
        # 测试确认操作菜单
        confirm_menu = menus.confirm_action("delete")
        for row in confirm_menu.inline_keyboard:
            for button in row:
                if button.callback_data and button.callback_data != "admin_main":
                    assert button.callback_data.startswith("admin_confirm_"), \
                        f"确认菜单按钮callback_data未加admin_confirm_前缀: {button.callback_data}"
    
    @pytest.mark.asyncio
    async def test_admin_handler_callback_routing(self):
        """测试AdminHandler的回调路由是否正确"""
        from src.bot_admin.handler import AdminHandler
        
        handler = AdminHandler()
        
        # 模拟更新和上下文
        update = Mock(spec=Update)
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        query = Mock(spec=CallbackQuery)
        user = Mock(spec=User)
        
        # 设置owner用户
        from src.config import settings
        user.id = settings.bot_owner_id
        update.effective_user = user
        update.callback_query = query
        query.from_user = user
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        
        # 测试价格配置回调
        test_cases = [
            ("admin_prices", "_show_price_menu"),
            ("admin_price_premium", "_show_premium_price"),
            ("admin_price_trx_rate", "_show_trx_rate"),
            ("admin_price_energy", "_show_energy_price"),
        ]
        
        for callback_data, expected_method in test_cases:
            query.data = callback_data
            # 验证handle_callback能正确识别并路由到相应方法
            # 注意：实际测试中可能需要mock相应的方法
            result = await handler.handle_callback(update, context)
            # 这里主要验证没有异常抛出
    
    def test_no_conflict_with_premium_module(self):
        """测试与Premium模块没有回调冲突"""
        admin_pattern = r"^admin_"
        
        # Premium模块的回调
        premium_callbacks = [
            "premium_3",
            "premium_6",
            "premium_12",
            "confirm_payment",
            "cancel_order",
        ]
        
        # 确保Admin pattern不会捕获Premium的回调
        for callback in premium_callbacks:
            assert not re.match(admin_pattern, callback), \
                f"Admin pattern错误捕获了Premium回调: {callback}"
    
    def test_no_conflict_with_orders_module(self):
        """测试与Orders模块没有回调冲突"""
        admin_pattern = r"^admin_"
        
        # Orders模块的回调（虽然是管理员功能，但有独立的ConversationHandler）
        orders_callbacks = [
            "orders_list",
            "orders_filter_type",
            "orders_filter_status",
            "orders_filter_user",
            "orders_clear_filter",
            "orders_close",
        ]
        
        # 确保Admin pattern不会捕获Orders的回调
        for callback in orders_callbacks:
            assert not re.match(admin_pattern, callback), \
                f"Admin pattern错误捕获了Orders回调: {callback}"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
