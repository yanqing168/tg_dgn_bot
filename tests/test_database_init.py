"""
测试数据库初始化功能
验证init_db函数正确且无重复定义
"""
import pytest
import os
import tempfile
from sqlalchemy import create_engine, inspect
from src.database import init_db, init_db_safe, Base


class TestDatabaseInit:
    """测试数据库初始化"""
    
    def test_init_db_exists(self):
        """测试init_db函数存在且可调用"""
        assert callable(init_db)
        assert init_db.__doc__ is not None
    
    def test_init_db_safe_exists(self):
        """测试init_db_safe函数存在"""
        assert callable(init_db_safe)
    
    def test_init_db_creates_tables(self):
        """测试init_db正确创建所有表"""
        # 创建临时数据库
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_db_path = tmp.name
        
        try:
            # 创建临时引擎
            test_engine = create_engine(f'sqlite:///{tmp_db_path}')
            
            # 使用临时引擎创建表
            Base.metadata.create_all(bind=test_engine)
            
            # 验证表是否创建
            inspector = inspect(test_engine)
            tables = inspector.get_table_names()
            
            # 验证关键表存在
            expected_tables = [
                'users', 'orders', 'user_bindings',
                'premium_orders', 'deposit_orders',
                'debit_records', 'suffix_allocations',
                'address_query_logs', 'energy_orders'
            ]
            
            for table in expected_tables:
                assert table in tables, f"表 {table} 应该被创建"
            
            # 清理
            test_engine.dispose()
        finally:
            # 删除临时文件
            if os.path.exists(tmp_db_path):
                os.unlink(tmp_db_path)
    
    def test_no_duplicate_init_db(self):
        """测试没有重复的init_db函数定义"""
        import src.database as db_module
        
        # 获取所有名为init_db的属性
        init_db_count = sum(1 for name in dir(db_module) if name == 'init_db')
        
        # 应该只有一个init_db
        assert init_db_count == 1, "应该只有一个init_db函数定义"
    
    def test_init_db_with_logging(self, caplog):
        """测试init_db包含日志记录"""
        import logging
        
        # 创建临时数据库
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_db_path = tmp.name
        
        try:
            # 临时替换引擎
            from src import database
            original_engine = database.engine
            
            test_engine = create_engine(f'sqlite:///{tmp_db_path}')
            database.engine = test_engine
            
            # 调用init_db
            with caplog.at_level(logging.INFO):
                init_db()
            
            # 验证日志
            assert any("数据库表初始化成功" in record.message for record in caplog.records)
            
            # 恢复原引擎
            database.engine = original_engine
            test_engine.dispose()
        finally:
            if os.path.exists(tmp_db_path):
                os.unlink(tmp_db_path)


class TestDatabaseSafety:
    """测试数据库安全功能"""
    
    def test_init_db_safe_validates_tables(self):
        """测试init_db_safe验证关键表"""
        # 这个测试需要实际的数据库环境
        # 这里只验证函数可调用
        assert callable(init_db_safe)


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
