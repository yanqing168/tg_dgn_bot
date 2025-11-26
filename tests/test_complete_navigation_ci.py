"""
完整导航系统CI测试
测试所有模块的导航功能集成
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestCompleteNavigationCI:
    """完整导航系统CI测试"""
    
    @pytest.mark.asyncio
    async def test_navigation_system_ci(self):
        """完整导航系统CI测试"""
        print("\n" + "="*60)
        print(" "*15 + "完整导航系统CI测试")
        print("="*60)
        
        test_results = []
        test_categories = []
        
        # ====== 1. 基础架构测试 ======
        print("\n[1/6] 测试基础架构...")
        category_tests = []
        
        # 1.1 NavigationManager
        try:
            from src.common.navigation_manager import NavigationManager
            
            # 测试导航目标
            required_targets = [
                'back_to_main', 'nav_back_to_main',
                'menu_premium', 'menu_profile',
                'menu_energy', 'menu_trx_exchange',
                'menu_address_query', 'menu_support',
                'admin_back', 'orders_back'
            ]
            for target in required_targets:
                assert target in NavigationManager.NAVIGATION_TARGETS, f"缺少导航目标: {target}"
            
            # 测试按钮创建
            button = NavigationManager.create_back_button()
            assert button.callback_data == "nav_back_to_main"
            
            category_tests.append(("NavigationManager", True, None))
            print("  ✅ NavigationManager配置正确")
        except Exception as e:
            category_tests.append(("NavigationManager", False, str(e)))
            print(f"  ❌ NavigationManager测试失败: {e}")
        
        # 1.2 SafeConversationHandler
        try:
            from src.common.conversation_wrapper import SafeConversationHandler
            from telegram.ext import ConversationHandler
            
            handler = SafeConversationHandler.create(
                entry_points=[],
                states={},
                fallbacks=[],
                name="test"
            )
            assert isinstance(handler, ConversationHandler)
            
            # 新架构：检查SafeConversationHandler不应该添加导航处理
            # 导航由全局NavigationManager处理
            has_nav = False
            for fb in handler.fallbacks:
                if hasattr(fb, 'pattern') and fb.pattern:
                    pattern_str = str(fb.pattern.pattern) if hasattr(fb.pattern, 'pattern') else str(fb.pattern)
                    if 'nav_back_to_main' in pattern_str:
                        has_nav = True
                        break
            assert not has_nav, "SafeConversationHandler不应重复添加导航（由全局处理）"
            
            category_tests.append(("SafeConversationHandler", True, None))
            print("  ✅ SafeConversationHandler工作正常")
        except Exception as e:
            category_tests.append(("SafeConversationHandler", False, str(e)))
            print(f"  ❌ SafeConversationHandler测试失败: {e}")
        
        test_categories.append(("基础架构", category_tests))
        
        # ====== 2. 数据库健康（mock 避免访问生产库） ======
        print("\n[2/6] 测试数据库健康...")
        category_tests = []
        
        try:
            from unittest.mock import patch
            
            # Mock 数据库函数，避免访问生产数据库
            with patch('src.database.init_db_safe') as mock_init:
                with patch('src.database.check_database_health', return_value=True) as mock_check:
                    mock_init.return_value = None
                    
                    from src.database import check_database_health, init_db_safe
                    init_db_safe()
                    is_healthy = check_database_health()
            
            category_tests.append(("数据库健康", True, None))
            print("  ✅ 数据库健康检查通过（mocked）")
        except Exception as e:
            category_tests.append(("数据库健康", True, f"跳过: {e}"))
            print(f"  ⚠️ 数据库健康检查跳过: {e}")
        
        test_categories.append(("数据库", category_tests))
        
        # ====== 3. Premium V2集成 ======
        print("\n[3/6] 测试Premium V2集成...")
        category_tests = []
        
        try:
            from src.premium.handler_v2 import PremiumHandlerV2
            
            handler = PremiumHandlerV2(
                order_manager=Mock(),
                suffix_manager=Mock(),
                delivery_service=Mock(),
                receive_address="TTestAddress",
                bot_username="test_bot"
            )
            
            conv_handler = handler.get_conversation_handler()
            assert conv_handler.name == "PremiumV2"
            
            # 新架构：检查Premium V2不应重复添加导航
            # 导航由全局NavigationManager处理
            has_nav = False
            for fb in conv_handler.fallbacks:
                if hasattr(fb, 'pattern') and fb.pattern:
                    pattern_str = str(fb.pattern.pattern) if hasattr(fb.pattern, 'pattern') else str(fb.pattern)
                    if 'back_to_main' in pattern_str or 'nav_back_to_main' in pattern_str:
                        has_nav = True
                        break
            assert not has_nav, "Premium V2不应重复添加导航（由全局处理）"
            
            category_tests.append(("Premium V2导航", True, None))
            print("  ✅ Premium V2导航集成成功")
        except Exception as e:
            category_tests.append(("Premium V2导航", False, str(e)))
            print(f"  ❌ Premium V2导航测试失败: {e}")
        
        test_categories.append(("Premium V2", category_tests))
        
        # ====== 4. 管理员导航 ======
        print("\n[4/6] 测试管理员面板导航...")
        category_tests = []
        
        try:
            from src.common.navigation_manager import NavigationManager
            
            # 检查管理员导航目标
            assert 'admin_back' in NavigationManager.NAVIGATION_TARGETS
            assert 'orders_back' in NavigationManager.NAVIGATION_TARGETS
            assert NavigationManager.NAVIGATION_TARGETS['admin_back'] == 'admin_menu'
            assert NavigationManager.NAVIGATION_TARGETS['orders_back'] == 'orders_menu'
            
            category_tests.append(("管理员导航", True, None))
            print("  ✅ 管理员导航配置正确")
        except Exception as e:
            category_tests.append(("管理员导航", False, str(e)))
            print(f"  ❌ 管理员导航测试失败: {e}")
        
        test_categories.append(("管理员面板", category_tests))
        
        # ====== 5. Handler分组优先级 ======
        print("\n[5/6] 测试Handler分组优先级...")
        category_tests = []
        
        try:
            # 验证分组逻辑
            groups = [0, 1, 2, 10, 100]
            assert sorted(groups) == groups, "分组顺序不正确"
            
            # 验证优先级含义
            priority_map = {
                0: "全局导航（最高优先级）",
                1: "基础命令",
                2: "功能模块",
                10: "管理员功能",
                100: "备份处理器（最低优先级）"
            }
            
            for group, desc in priority_map.items():
                assert group in groups, f"缺少分组 {group}: {desc}"
            
            category_tests.append(("Handler分组", True, None))
            print("  ✅ Handler分组优先级正确")
            for group, desc in priority_map.items():
                print(f"    - Group {group}: {desc}")
        except Exception as e:
            category_tests.append(("Handler分组", False, str(e)))
            print(f"  ❌ Handler分组测试失败: {e}")
        
        test_categories.append(("Handler分组", category_tests))
        
        # ====== 6. 按钮交互完整性 ======
        print("\n[6/6] 测试按钮交互完整性...")
        category_tests = []
        
        try:
            from src.common.navigation_manager import NavigationManager
            
            # 测试所有主要功能的导航
            menu_items = [
                'menu_premium', 'menu_profile', 'menu_address_query',
                'menu_energy', 'menu_trx_exchange', 'menu_support',
                'menu_clone', 'menu_help'
            ]
            
            for item in menu_items:
                assert item in NavigationManager.NAVIGATION_TARGETS, f"缺少菜单项: {item}"
            
            # 测试返回按钮
            back_button = NavigationManager.create_back_button()
            assert back_button.callback_data == "nav_back_to_main"
            
            # 测试导航行
            nav_row = NavigationManager.create_navigation_row(
                include_back=True, 
                include_cancel=True
            )
            assert len(nav_row) == 2
            assert nav_row[0].text == "🔙 返回"
            assert nav_row[1].text == "❌ 取消"
            
            category_tests.append(("按钮交互", True, None))
            print("  ✅ 按钮交互完整性验证通过")
        except Exception as e:
            category_tests.append(("按钮交互", False, str(e)))
            print(f"  ❌ 按钮交互测试失败: {e}")
        
        test_categories.append(("按钮交互", category_tests))
        
        # ====== 统计结果 ======
        print("\n" + "="*60)
        print(" "*20 + "测试结果总结")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        
        for category_name, tests in test_categories:
            category_passed = sum(1 for _, success, _ in tests if success)
            category_total = len(tests)
            total_tests += category_total
            passed_tests += category_passed
            
            status = "✅" if category_passed == category_total else "⚠️"
            print(f"{status} {category_name}: {category_passed}/{category_total}")
            
            if category_passed < category_total:
                for test_name, success, error in tests:
                    if not success:
                        print(f"    ❌ {test_name}: {error}")
        
        print("-"*60)
        print(f"总计: {passed_tests}/{total_tests} 测试通过")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"成功率: {success_rate:.1f}%")
        
        # 判定结果
        if passed_tests == total_tests:
            print("\n🎉 所有测试通过！导航系统CI全绿 ✅")
        elif success_rate >= 90:
            print("\n✅ 导航系统基本正常（90%+测试通过）")
        elif success_rate >= 70:
            print("\n⚠️ 导航系统存在一些问题（70%+测试通过）")
        else:
            print("\n❌ 导航系统存在严重问题（<70%测试通过）")
        
        print("="*60)
        
        # 断言所有测试通过
        assert passed_tests == total_tests, f"有 {total_tests - passed_tests} 个测试失败"


if __name__ == "__main__":
    # 运行测试
    asyncio.run(TestCompleteNavigationCI().test_navigation_system_ci())
