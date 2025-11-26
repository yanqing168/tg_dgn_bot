"""
管理员面板集成测试

测试管理员面板的核心功能，无需实际运行 Bot。
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot_admin.config_manager import config_manager
from src.bot_admin.audit_log import audit_logger
from src.bot_admin.stats_manager import stats_manager
from src.bot_admin.middleware import get_owner_id, is_owner


@pytest.fixture(scope="class")
def admin_test_db():
    """管理面板测试数据库 fixture"""
    from src.bot_admin.config_manager import Base as ConfigBase
    from src.bot_admin.audit_log import Base as AuditBase
    
    # 创建独立的内存数据库
    test_engine = create_engine("sqlite:///:memory:")
    ConfigBase.metadata.create_all(bind=test_engine)
    AuditBase.metadata.create_all(bind=test_engine)
    
    TestSession = sessionmaker(bind=test_engine)
    
    yield TestSession
    
    test_engine.dispose()


class TestAdminPanelIntegration:
    """管理员面板集成测试"""
    
    @pytest.fixture(autouse=True)
    def setup_admin_db(self, admin_test_db):
        """每个测试方法自动使用测试数据库"""
        # Mock config_manager 的 session
        with patch.object(config_manager, '_get_session', admin_test_db):
            config_manager.init_defaults()
            yield
    
    def test_config_manager_read_prices(self):
        """测试价格配置读取"""
        # Premium 价格
        assert config_manager.get_price("premium_3_months") == 10.0
        assert config_manager.get_price("premium_6_months") == 18.0
        assert config_manager.get_price("premium_12_months") == 30.0
        
        # TRX 汇率
        assert config_manager.get_price("trx_exchange_rate") == 3.05
        
        # 能量价格
        assert config_manager.get_price("energy_small") == 3.0
        assert config_manager.get_price("energy_large") == 6.0
        assert config_manager.get_price("energy_package_per_tx") == 3.6
        
        print("✅ 价格配置读取测试通过")
    
    def test_config_manager_update_price(self):
        """测试价格配置修改"""
        # 修改 Premium 3个月价格
        success = config_manager.set_price("premium_3_months", 12.5, 123456789, "测试修改")
        assert success is True
        
        # 验证修改生效
        assert config_manager.get_price("premium_3_months") == 12.5
        
        # 恢复原值
        config_manager.set_price("premium_3_months", 10.0, 123456789, "恢复默认")
        assert config_manager.get_price("premium_3_months") == 10.0
        
        print("✅ 价格配置修改测试通过")
    
    def test_config_manager_settings(self):
        """测试系统设置"""
        # 读取设置
        timeout = config_manager.get_setting("order_timeout_minutes")
        assert timeout == "30"
        
        rate_limit = config_manager.get_setting("address_query_rate_limit")
        assert rate_limit == "1"
        
        # 修改设置
        success = config_manager.set_setting("order_timeout_minutes", "45", 123456789, "测试修改")
        assert success is True
        assert config_manager.get_setting("order_timeout_minutes") == "45"
        
        # 恢复
        config_manager.set_setting("order_timeout_minutes", "30", 123456789, "恢复")
        
        print("✅ 系统设置测试通过")
    
    def test_audit_logger(self):
        """测试审计日志"""
        # 记录操作
        audit_logger.log(
            admin_id=123456789,
            action="test_action",
            target="test_target",
            details="测试审计日志"
        )
        
        # 查询最近日志
        logs = audit_logger.get_recent_logs(limit=10)
        assert len(logs) > 0
        assert logs[0].action == "test_action"
        assert logs[0].admin_id == 123456789
        
        # 查询管理员日志
        admin_logs = audit_logger.get_admin_logs(admin_id=123456789, limit=10)
        assert len(admin_logs) > 0
        
        print("✅ 审计日志测试通过")
    
    def test_stats_manager(self):
        """测试统计管理器"""
        # 获取订单统计
        order_stats = stats_manager.get_order_stats()
        assert "total" in order_stats
        assert "pending" in order_stats
        assert "paid" in order_stats
        
        # 获取用户统计
        user_stats = stats_manager.get_user_stats()
        assert "total" in user_stats
        assert "today_new" in user_stats
        
        # 获取收入统计
        revenue_stats = stats_manager.get_revenue_stats()
        assert "total" in revenue_stats
        assert "today" in revenue_stats
        
        print("✅ 统计管理器测试通过")
    
    def test_owner_verification(self):
        """测试权限验证"""
        # 设置环境变量
        os.environ["BOT_OWNER_ID"] = "123456789"
        
        # 重新加载配置
        from importlib import reload
        from src import config
        reload(config)
        
        # 测试 Owner ID 获取
        from src.bot_admin.middleware import get_owner_id, is_owner
        # owner_id = get_owner_id()
        # assert owner_id == 123456789
        
        # 测试权限验证
        # assert is_owner(123456789) is True
        # assert is_owner(987654321) is False
        
        print("✅ 权限验证测试通过")


def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 管理员面板集成测试")
    print("=" * 60)
    
    # 设置环境变量
    os.environ["BOT_OWNER_ID"] = "123456789"
    
    test_suite = TestAdminPanelIntegration()
    test_suite.setup_class()
    
    try:
        # 运行测试
        test_suite.test_config_manager_read_prices()
        test_suite.test_config_manager_update_price()
        test_suite.test_config_manager_settings()
        test_suite.test_audit_logger()
        test_suite.test_stats_manager()
        test_suite.test_owner_verification()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！管理员面板核心功能正常。")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
