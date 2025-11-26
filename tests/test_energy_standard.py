"""
测试标准化的能量模块
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, CallbackQuery, Message, Chat
from telegram.ext import ContextTypes, ConversationHandler

from src.modules.energy.handler import EnergyModule
from src.modules.energy.messages import EnergyMessages
from src.modules.energy.states import *
from src.core.state_manager import ModuleStateManager


class MockContext:
    """模拟Context对象"""
    def __init__(self):
        self.user_data = {}
        self.chat_data = {}
        self.bot_data = {}


def create_mock_update(callback_data=None, message_text=None):
    """创建模拟的Update对象"""
    update = MagicMock(spec=Update)
    
    if callback_data:
        # 模拟CallbackQuery
        query = MagicMock(spec=CallbackQuery)
        query.data = callback_data
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.message = MagicMock(spec=Message)
        query.message.chat = MagicMock(spec=Chat)
        query.message.chat.id = 123456
        update.callback_query = query
        update.message = None
    else:
        # 模拟Message
        message = MagicMock(spec=Message)
        message.text = message_text or ""
        message.reply_text = AsyncMock()
        message.chat = MagicMock(spec=Chat)
        message.chat.id = 123456
        update.message = message
        update.callback_query = None
    
    return update


@pytest.fixture
def energy_module():
    """创建能量模块实例"""
    return EnergyModule()


class TestEnergyModule:
    """测试能量模块"""
    
    def test_module_properties(self, energy_module):
        """测试模块属性"""
        assert energy_module.module_name == "energy"
        handlers = energy_module.get_handlers()
        assert len(handlers) == 1
        assert isinstance(handlers[0], ConversationHandler)
    
    @pytest.mark.asyncio
    async def test_start_energy_with_callback(self, energy_module):
        """测试通过CallbackQuery启动能量兑换"""
        update = create_mock_update(callback_data="energy")
        context = MockContext()
        
        result = await energy_module.start_energy(update, context)
        
        assert result == STATE_SELECT_TYPE
        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()
        
        # 验证消息包含HTML标签
        call_args = update.callback_query.edit_message_text.call_args
        assert "<b>" in call_args[1]["text"]
        assert call_args[1]["parse_mode"] == "HTML"
    
    @pytest.mark.asyncio
    async def test_start_energy_with_message(self, energy_module):
        """测试通过Message启动能量兑换"""
        update = create_mock_update(message_text="/energy")
        context = MockContext()
        
        result = await energy_module.start_energy(update, context)
        
        assert result == STATE_SELECT_TYPE
        update.message.reply_text.assert_called_once()
        
        # 验证消息格式
        call_args = update.message.reply_text.call_args
        assert "<b>" in call_args[1]["text"]
        assert call_args[1]["parse_mode"] == "HTML"
    
    @pytest.mark.asyncio
    async def test_select_type_hourly(self, energy_module):
        """测试选择时长能量"""
        update = create_mock_update(callback_data="energy_type_hourly")
        context = MockContext()
        
        result = await energy_module.select_type(update, context)
        
        assert result == STATE_SELECT_PACKAGE
        update.callback_query.answer.assert_called_once()
        
        # 验证状态已保存 - 直接检查context.user_data
        assert "energy_type" in context.user_data
    
    @pytest.mark.asyncio
    async def test_select_type_package(self, energy_module):
        """测试选择笔数套餐"""
        update = create_mock_update(callback_data="energy_type_package")
        context = MockContext()
        
        result = await energy_module.select_type(update, context)
        
        assert result == STATE_INPUT_USDT
        
        # 验证状态 - 直接检查context.user_data
        assert "energy_type" in context.user_data
    
    @pytest.mark.asyncio
    async def test_select_type_flash(self, energy_module):
        """测试选择闪兑"""
        update = create_mock_update(callback_data="energy_type_flash")
        context = MockContext()
        
        result = await energy_module.select_type(update, context)
        
        assert result == STATE_INPUT_USDT
    
    @pytest.mark.asyncio
    async def test_select_package_65k(self, energy_module):
        """测试选择6.5万能量套餐"""
        update = create_mock_update(callback_data="energy_pkg_65k")
        context = MockContext()
        
        result = await energy_module.select_package_callback(update, context)
        
        assert result == STATE_INPUT_ADDRESS
        
        # 验证套餐信息已保存 - 直接检查context.user_data
        assert context.user_data.get("energy_amount") == 65000
        assert context.user_data.get("price_trx") == 3
    
    @pytest.mark.asyncio
    async def test_select_package_131k(self, energy_module):
        """测试选择13.1万能量套餐"""
        update = create_mock_update(callback_data="energy_pkg_131k")
        context = MockContext()
        
        result = await energy_module.select_package_callback(update, context)
        
        assert result == STATE_INPUT_ADDRESS
        
        # 验证套餐信息 - 直接检查context.user_data
        assert context.user_data.get("energy_amount") == 131000
        assert context.user_data.get("price_trx") == 6
    
    @pytest.mark.asyncio
    @patch('src.modules.energy.handler.AddressValidator')
    async def test_input_address_valid(self, mock_validator, energy_module):
        """测试输入有效地址"""
        mock_validator_instance = mock_validator.return_value
        mock_validator_instance.validate.return_value = (True, None)
        energy_module.validator = mock_validator_instance
        
        update = create_mock_update(message_text="TValidAddress123456789012345678901234")
        context = MockContext()
        
        # 设置必要的状态 - 直接设置context.user_data
        context.user_data["energy_type"] = "hourly"
        context.user_data["energy_amount"] = 65000
        context.user_data["price_trx"] = 3
        
        with patch.object(energy_module, '_show_payment_info', return_value=STATE_SHOW_PAYMENT):
            result = await energy_module.input_address(update, context)
        
        assert result == STATE_SHOW_PAYMENT
        
        # 验证地址已保存 - 直接检查context.user_data
        assert context.user_data.get("receive_address") == "TValidAddress123456789012345678901234"
    
    @pytest.mark.asyncio
    @patch('src.modules.energy.handler.AddressValidator')
    async def test_input_address_invalid(self, mock_validator, energy_module):
        """测试输入无效地址"""
        mock_validator_instance = mock_validator.return_value
        mock_validator_instance.validate.return_value = (False, "地址格式错误")
        energy_module.validator = mock_validator_instance
        
        update = create_mock_update(message_text="invalid_address")
        context = MockContext()
        
        result = await energy_module.input_address(update, context)
        
        assert result == STATE_INPUT_ADDRESS
        update.message.reply_text.assert_called_once()
        
        # 验证错误消息
        call_args = update.message.reply_text.call_args
        assert "无效" in call_args[1]["text"]
    
    @pytest.mark.asyncio
    async def test_input_usdt_amount_valid(self, energy_module):
        """测试输入有效USDT金额"""
        update = create_mock_update(message_text="10")
        context = MockContext()
        
        # 设置笔数套餐类型 - 直接设置context.user_data
        context.user_data["energy_type"] = "package"
        
        result = await energy_module.input_usdt_amount(update, context)
        
        assert result == STATE_INPUT_ADDRESS
        assert context.user_data.get("usdt_amount") == 10.0
    
    @pytest.mark.asyncio
    async def test_input_usdt_amount_too_low(self, energy_module):
        """测试输入过低的USDT金额"""
        update = create_mock_update(message_text="2")
        context = MockContext()
        
        # 设置笔数套餐类型（最低5 USDT） - 直接设置context.user_data
        context.user_data["energy_type"] = "package"
        
        result = await energy_module.input_usdt_amount(update, context)
        
        assert result == STATE_INPUT_USDT
        update.message.reply_text.assert_called_once()
        
        # 验证错误消息
        call_args = update.message.reply_text.call_args
        assert "最低" in call_args[1]["text"] or "无效" in call_args[1]["text"]
    
    @pytest.mark.asyncio
    async def test_back_to_type(self, energy_module):
        """测试返回类型选择"""
        update = create_mock_update(callback_data="energy_back")
        context = MockContext()
        
        # 设置一些状态 - 直接设置context.user_data
        context.user_data["energy_type"] = "hourly"
        context.user_data["energy_amount"] = 65000
        
        result = await energy_module.back_to_type(update, context)
        
        assert result == STATE_SELECT_TYPE
        
        # 验证状态已清除 - 直接检查context.user_data
        assert "energy_type" not in context.user_data
        assert "energy_amount" not in context.user_data
    
    @pytest.mark.asyncio
    async def test_message_templates_html_format(self):
        """测试所有消息模板都是HTML格式"""
        assert "<b>" in EnergyMessages.MAIN_MENU
        assert "<b>" in EnergyMessages.HOURLY_PACKAGES
        assert "<b>" in EnergyMessages.PACKAGE_INFO
        assert "<b>" in EnergyMessages.FLASH_EXCHANGE
        assert "<b>" in EnergyMessages.INPUT_ADDRESS
        assert "<b>" in EnergyMessages.PAYMENT_INFO_HOURLY
        assert "<b>" in EnergyMessages.PAYMENT_INFO_USDT
    
    def test_state_manager_integration(self, energy_module):
        """测试状态管理器集成"""
        context = MockContext()
        
        # 初始化状态
        ModuleStateManager.init_state(context, "energy")
        
        # 获取状态
        state = ModuleStateManager.get_state(context, "energy")
        assert isinstance(state, dict)
        
        # 设置状态
        state["test_key"] = "test_value"
        assert state["test_key"] == "test_value"
        
        # 清理状态
        ModuleStateManager.clear_state(context, "energy")
        state = ModuleStateManager.get_state(context, "energy")
        assert "test_key" not in state


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
