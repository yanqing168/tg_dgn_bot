"""
核心基础设施测试
测试MessageFormatter、ModuleStateManager等核心组件
"""

import pytest
from unittest.mock import MagicMock
from telegram.ext import ContextTypes

from src.core.formatter import MessageFormatter
from src.core.state_manager import ModuleStateManager
from src.core.base import BaseModule


class MockContext:
    """模拟Context对象"""
    def __init__(self):
        self.user_data = {}
        self.chat_data = {}
        self.bot_data = {}


class TestMessageFormatter:
    """测试消息格式化器"""
    
    def test_escape_html(self):
        """测试HTML转义"""
        # 测试空字符串
        assert MessageFormatter.escape_html("") == ""
        assert MessageFormatter.escape_html(None) == ""
        
        # 测试普通文本
        assert MessageFormatter.escape_html("hello") == "hello"
        
        # 测试特殊字符
        assert MessageFormatter.escape_html("<script>") == "&lt;script&gt;"
        assert MessageFormatter.escape_html("a & b") == "a &amp; b"
        assert MessageFormatter.escape_html('"test"') == '&quot;test&quot;'
        
        # 测试组合
        assert MessageFormatter.escape_html('<a href="test">link</a>') == '&lt;a href=&quot;test&quot;&gt;link&lt;/a&gt;'
    
    def test_escape_markdown(self):
        """测试Markdown V1转义"""
        # 测试空字符串
        assert MessageFormatter.escape_markdown("") == ""
        assert MessageFormatter.escape_markdown(None) == ""
        
        # 测试特殊字符
        assert MessageFormatter.escape_markdown("test_user") == r"test\_user"
        assert MessageFormatter.escape_markdown("*bold*") == r"\*bold\*"
        assert MessageFormatter.escape_markdown("[link](url)") == r"\[link\]\(url\)"
    
    def test_format_html(self):
        """测试HTML格式化"""
        # 测试基本格式化
        template = "Hello {name}"
        result = MessageFormatter.format_html(template, name="World")
        assert result == "Hello World"
        
        # 测试自动转义
        template = "用户：{username}"
        result = MessageFormatter.format_html(template, username="<test>")
        assert result == "用户：&lt;test&gt;"
        
        # 测试None值
        template = "用户：{username}，昵称：{nickname}"
        result = MessageFormatter.format_html(template, username=None, nickname="Test")
        assert result == "用户：，昵称：Test"
        
        # 测试多个参数
        template = "订单 {order_id}：{amount} USDT"
        result = MessageFormatter.format_html(template, order_id="ORDER001", amount=10.5)
        assert result == "订单 ORDER001：10.5 USDT"
    
    def test_safe_username(self):
        """测试安全用户名格式化"""
        # HTML格式
        assert MessageFormatter.safe_username(None) == "未设置"
        assert MessageFormatter.safe_username("") == "未设置"
        assert MessageFormatter.safe_username("alice") == "@alice"
        assert MessageFormatter.safe_username("<test>") == "@&lt;test&gt;"
        
        # Markdown格式
        assert MessageFormatter.safe_username("test_user", MessageFormatter.FORMAT_MARKDOWN) == r"@test\_user"
        
        # 普通格式
        assert MessageFormatter.safe_username("test", "PLAIN") == "@test"
    
    def test_safe_nickname(self):
        """测试安全昵称格式化"""
        # HTML格式
        assert MessageFormatter.safe_nickname(None) == "未知"
        assert MessageFormatter.safe_nickname("") == "未知"
        assert MessageFormatter.safe_nickname("Alice") == "Alice"
        assert MessageFormatter.safe_nickname("<script>") == "&lt;script&gt;"
        
        # Markdown格式
        assert MessageFormatter.safe_nickname("test_user", MessageFormatter.FORMAT_MARKDOWN) == r"test\_user"


class TestModuleStateManager:
    """测试模块状态管理器"""
    
    def test_init_state(self):
        """测试初始化状态"""
        context = MockContext()
        
        # 第一次初始化
        state = ModuleStateManager.init_state(context, "test_module")
        assert isinstance(state, dict)
        assert 'modules' in context.user_data
        assert 'test_module' in context.user_data['modules']
        
        # 再次初始化不会清空已有数据
        state['key1'] = 'value1'
        state2 = ModuleStateManager.init_state(context, "test_module")
        assert state2['key1'] == 'value1'
    
    def test_get_state(self):
        """测试获取状态"""
        context = MockContext()
        
        # 不存在的模块返回空字典
        state = ModuleStateManager.get_state(context, "non_existent")
        assert state == {}
        
        # 存在的模块
        ModuleStateManager.init_state(context, "test_module")
        context.user_data['modules']['test_module']['key1'] = 'value1'
        state = ModuleStateManager.get_state(context, "test_module")
        assert state['key1'] == 'value1'
    
    def test_set_and_get_value(self):
        """测试设置和获取单个值"""
        context = MockContext()
        
        # 设置值
        ModuleStateManager.set_state(context, "test_module", "key1", "value1")
        assert 'modules' in context.user_data
        assert 'test_module' in context.user_data['modules']
        assert context.user_data['modules']['test_module']['key1'] == 'value1'
        
        # 获取值
        value = ModuleStateManager.get_value(context, "test_module", "key1")
        assert value == "value1"
        
        # 获取不存在的值
        value = ModuleStateManager.get_value(context, "test_module", "key2")
        assert value is None
        
        # 获取带默认值
        value = ModuleStateManager.get_value(context, "test_module", "key2", "default")
        assert value == "default"
    
    def test_clear_state(self):
        """测试清理状态"""
        context = MockContext()
        
        # 设置状态
        ModuleStateManager.init_state(context, "module1")
        ModuleStateManager.init_state(context, "module2")
        context.user_data['modules']['module1']['key1'] = 'value1'
        context.user_data['modules']['module2']['key2'] = 'value2'
        
        # 清理module1
        ModuleStateManager.clear_state(context, "module1")
        assert 'module1' not in context.user_data['modules']
        assert 'module2' in context.user_data['modules']
        assert context.user_data['modules']['module2']['key2'] == 'value2'
    
    def test_clear_all_module_states(self):
        """测试清理所有模块状态但保留全局键"""
        context = MockContext()
        
        # 设置全局数据和模块数据
        context.user_data['user_id'] = 123456
        context.user_data['username'] = 'testuser'
        context.user_data['other_key'] = 'other_value'
        
        ModuleStateManager.init_state(context, "module1")
        context.user_data['modules']['module1']['key1'] = 'value1'
        
        # 清理所有模块状态
        ModuleStateManager.clear_all_module_states(context)
        
        # 验证全局键被保留
        assert context.user_data['user_id'] == 123456
        assert context.user_data['username'] == 'testuser'
        
        # 验证非保留键被清理
        assert 'other_key' not in context.user_data
        
        # 验证模块数据被清理
        assert context.user_data['modules'] == {}
    
    def test_has_state(self):
        """测试检查状态是否存在"""
        context = MockContext()
        
        # 不存在的模块
        assert ModuleStateManager.has_state(context, "test_module") == False
        
        # 存在的模块
        ModuleStateManager.init_state(context, "test_module")
        assert ModuleStateManager.has_state(context, "test_module") == True


class TestBaseModule:
    """测试基类"""
    
    def test_base_module_abstract(self):
        """测试基类不能直接实例化"""
        with pytest.raises(TypeError):
            BaseModule()
    
    def test_base_module_implementation(self):
        """测试基类实现"""
        class TestModule(BaseModule):
            @property
            def module_name(self):
                return "test"
            
            def get_handlers(self):
                return []
        
        module = TestModule()
        assert module.module_name == "test"
        assert module.get_handlers() == []
        assert module.validate_config() == True
        
        # 测试可选方法
        module.on_startup()  # 不应该抛出异常
        module.on_shutdown()  # 不应该抛出异常


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
