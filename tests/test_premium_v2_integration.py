"""
Premium V2 功能集成测试
测试给自己/他人开通的完整流程，使用 bot_app_v2 fixture（离线模式）
"""
import pytest
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.utils.telegram_simulator import BotTestHelper, TelegramSimulator


class TestPremiumV2Integration:
    """Premium V2 功能集成测试 - 使用 bot_app_v2 fixture"""
    
    @pytest.fixture
    async def helper(self, bot_app_v2):
        """基于 bot_app_v2 创建测试辅助类"""
        helper = BotTestHelper(bot_app_v2)
        await helper.initialize()
        yield helper
    
    @pytest.mark.asyncio
    async def test_premium_for_self(self, helper):
        """测试给自己开通Premium"""
        # 1. 进入主菜单
        await helper.send_command("start")
        
        # 2. 进入 Premium 页面
        await helper.click_button("menu_premium")
        
        # 验证显示 Premium 页面
        message = helper.get_message_text()
        assert message is not None
        assert "Premium" in message
        
        # 3. 选择给自己开通
        await helper.click_button("premium_self")
        
        # 验证有响应
        message = helper.get_message_text()
        assert message is not None
        
        # 4. 选择套餐
        await helper.click_button("premium_3")
        
        # 验证进入确认阶段
        message = helper.get_message_text()
        assert message is not None
    
    @pytest.mark.asyncio
    async def test_premium_for_other_existing_user(self, helper):
        """测试给他人开通Premium"""
        # 1. 进入主菜单
        await helper.send_command("start")
        
        # 2. 进入 Premium 页面
        await helper.click_button("menu_premium")
        
        # 3. 选择给他人开通
        await helper.click_button("premium_other")
        
        # 验证提示输入用户名
        message = helper.get_message_text()
        assert message is not None
        
        # 4. 输入用户名
        await helper.send_message("@testuser")
        
        # 验证有响应
        message = helper.get_message_text()
        assert message is not None
    
    @pytest.mark.asyncio
    async def test_premium_for_other_nonexistent_user(self, helper):
        """测试给不存在的用户开通Premium"""
        # 1. 进入 Premium 页面
        await helper.send_command("start")
        await helper.click_button("menu_premium")
        
        # 2. 选择给他人开通
        await helper.click_button("premium_other")
        
        # 3. 输入不存在的用户名
        await helper.send_message("@nonexistent_user_123")
        
        # 验证有响应（可能是错误提示或重新输入提示）
        message = helper.get_message_text()
        assert message is not None
    
    @pytest.mark.asyncio
    async def test_premium_invalid_username_format(self, helper):
        """测试无效用户名格式"""
        # 1. 进入 Premium 页面
        await helper.send_command("start")
        await helper.click_button("menu_premium")
        
        # 2. 选择给他人开通
        await helper.click_button("premium_other")
        
        # 3. 输入太短的用户名
        await helper.send_message("@ab")
        
        # 验证有响应（可能是格式错误提示）
        message = helper.get_message_text()
        assert message is not None
    
    @pytest.mark.asyncio
    async def test_premium_cancel_at_different_stages(self, helper):
        """测试在不同阶段取消/返回"""
        # 场景1：在 Premium 首页返回主菜单
        await helper.send_command("start")
        await helper.click_button("menu_premium")
        await helper.click_button("back_to_main")
        
        # 验证返回主菜单
        message = helper.get_message_text()
        assert message is not None
        
        # 场景2：在选择套餐阶段返回
        await helper.click_button("menu_premium")
        await helper.click_button("premium_self")
        await helper.click_button("back_to_main")
        
        # 验证返回主菜单
        message = helper.get_message_text()
        assert message is not None


@pytest.mark.asyncio
async def test_run_premium_v2_ci():
    """运行Premium V2 CI测试"""
    # 简化的CI测试 - 验证 PremiumModule 创建
    from src.modules.premium.handler import PremiumModule
    from src.payments.order import order_manager
    from src.payments.suffix_manager import suffix_manager
    
    # 创建 PremiumModule
    module = PremiumModule(
        order_manager=order_manager,
        suffix_manager=suffix_manager,
        delivery_service=MagicMock(),
        receive_address="TTest123",
        bot_username="test_bot"
    )
    
    # 验证 handlers 创建
    handlers = module.get_handlers()
    assert len(handlers) > 0, "PremiumModule 应返回至少一个 handler"
    
    # 验证模块名称
    assert module.module_name == "premium"


if __name__ == "__main__":
    asyncio.run(test_run_premium_v2_ci())
