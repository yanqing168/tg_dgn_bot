"""
测试新架构Bot V2
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.bot_v2 import TelegramBotV2
from src.core.registry import ModuleRegistry


@pytest.fixture
async def bot_v2():
    """创建Bot V2实例"""
    with patch('src.bot_v2.settings') as mock_settings:
        mock_settings.bot_token = "test_token"
        mock_settings.usdt_trc20_receive_addr = "test_address"
        mock_settings.bot_owner_id = 123456
        mock_settings.use_webhook = False
        
        bot = TelegramBotV2()
        return bot


class TestBotV2:
    """测试Bot V2"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, bot_v2):
        """测试初始化"""
        with patch('src.bot_v2.init_db_safe'):
            with patch('src.bot_v2.check_database_health', return_value=True):
                with patch('src.bot_v2.order_manager.connect', new_callable=AsyncMock):
                    with patch('src.bot_v2.suffix_manager.connect', new_callable=AsyncMock):
                        with patch('telegram.ext.Application.builder') as mock_builder:
                            mock_app = MagicMock()
                            mock_app.bot.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))
                            mock_builder.return_value.token.return_value.build.return_value = mock_app
                            
                            await bot_v2.initialize()
                            
                            assert bot_v2.app is not None
                            assert bot_v2.api_app is not None
                            assert bot_v2.wallet_manager is not None
    
    def test_registry_integration(self, bot_v2):
        """测试模块注册中心集成"""
        assert bot_v2.registry is not None
        assert isinstance(bot_v2.registry, ModuleRegistry)
    
    @pytest.mark.asyncio
    async def test_module_registration(self, bot_v2):
        """测试模块注册"""
        with patch('src.bot_v2.init_db_safe'):
            with patch('src.bot_v2.check_database_health', return_value=True):
                with patch('src.bot_v2.order_manager.connect', new_callable=AsyncMock):
                    with patch('src.bot_v2.suffix_manager.connect', new_callable=AsyncMock):
                        with patch('telegram.ext.Application.builder') as mock_builder:
                            mock_app = MagicMock()
                            mock_app.bot.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))
                            mock_builder.return_value.token.return_value.build.return_value = mock_app
                            
                            await bot_v2.initialize()
                            
                            # 检查标准化模块是否注册
                            modules = bot_v2.registry.list_modules()
                            assert "main_menu" in modules
                            assert "premium" in modules
    
    @pytest.mark.asyncio
    async def test_api_app_creation(self, bot_v2):
        """测试API应用创建"""
        with patch('src.bot_v2.init_db_safe'):
            with patch('src.bot_v2.check_database_health', return_value=True):
                with patch('src.bot_v2.order_manager.connect', new_callable=AsyncMock):
                    with patch('src.bot_v2.suffix_manager.connect', new_callable=AsyncMock):
                        with patch('telegram.ext.Application.builder') as mock_builder:
                            mock_app = MagicMock()
                            mock_app.bot.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))
                            mock_builder.return_value.token.return_value.build.return_value = mock_app
                            
                            await bot_v2.initialize()
                            
                            assert bot_v2.api_app is not None
                            # 验证API路由存在
                            routes = [route.path for route in bot_v2.api_app.routes]
                            assert "/api/health" in routes
                            assert "/api/modules" in routes


class TestModuleRegistry:
    """测试模块注册中心"""
    
    def test_register_module(self):
        """测试注册模块"""
        from src.core.base import BaseModule
        
        registry = ModuleRegistry()
        
        class TestModule(BaseModule):
            @property
            def module_name(self):
                return "test"
            
            def get_handlers(self):
                return []
        
        module = TestModule()
        registry.register(module, priority=5, enabled=True)
        
        assert "test" in registry.list_modules()
        assert registry.get_module("test") == module
        assert registry.is_enabled("test") == True
    
    def test_enable_disable_module(self):
        """测试启用/禁用模块"""
        from src.core.base import BaseModule
        
        registry = ModuleRegistry()
        
        class TestModule(BaseModule):
            @property
            def module_name(self):
                return "test"
            
            def get_handlers(self):
                return []
        
        module = TestModule()
        registry.register(module, priority=5, enabled=True)
        
        # 禁用
        registry.disable_module("test")
        assert registry.is_enabled("test") == False
        
        # 启用
        registry.enable_module("test")
        assert registry.is_enabled("test") == True
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        from src.core.base import BaseModule
        
        registry = ModuleRegistry()
        
        class TestModule(BaseModule):
            @property
            def module_name(self):
                return "test"
            
            def get_handlers(self):
                return []
        
        module = TestModule()
        registry.register(module, priority=5, enabled=True)
        
        stats = registry.get_statistics()
        
        assert stats['total_modules'] == 1
        assert stats['enabled_modules'] == 1
        assert stats['disabled_modules'] == 0


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
