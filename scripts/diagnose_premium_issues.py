#!/usr/bin/env python3
"""
诊断Premium V2问题
分析：
1. 按钮点击错误
2. 返回按钮重复执行问题
"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_handler_registration():
    """检查handler注册情况"""
    print("\n=== 1. Handler注册分析 ===")
    print("-" * 40)
    
    issues = []
    
    # 检查bot.py
    bot_file = Path(__file__).parent.parent / "src" / "bot.py"
    with open(bot_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查Premium handler注册
    if "premium_handler.get_conversation_handler()" in content:
        # 查找注册的group
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "premium_handler.get_conversation_handler()" in line:
                # 查找group参数
                for j in range(max(0, i-2), min(len(lines), i+2)):
                    if "group=" in lines[j]:
                        group_num = lines[j].split("group=")[1].split(")")[0]
                        print(f"✓ Premium V2注册在group={group_num}")
                        break
    
    # 检查NavigationManager全局注册
    if "NavigationManager.handle_navigation" in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "NavigationManager.handle_navigation" in line:
                for j in range(max(0, i-2), min(len(lines), i+2)):
                    if "group=" in lines[j]:
                        group_num = lines[j].split("group=")[1].split(")")[0]
                        print(f"✓ NavigationManager全局注册在group={group_num}")
                        if group_num == "0":
                            print("  ⚠️ 全局导航在最高优先级，可能拦截其他处理器")
                        break
    
    return issues


def check_conversation_wrapper():
    """检查SafeConversationHandler的fallback配置"""
    print("\n=== 2. SafeConversationHandler分析 ===")
    print("-" * 40)
    
    wrapper_file = Path(__file__).parent.parent / "src" / "common" / "conversation_wrapper.py"
    with open(wrapper_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = []
    
    # 检查导航模式
    if "NAVIGATION_PATTERNS = [" in content:
        start = content.find("NAVIGATION_PATTERNS = [")
        end = content.find("]", start)
        patterns = content[start:end+1]
        print("导航模式:")
        for line in patterns.split('\n'):
            if "r'" in line or 'r"' in line:
                print(f"  - {line.strip()}")
    
    # 检查是否在fallback中重复添加导航
    if "safe_fallbacks.append" in content:
        lines = content.split('\n')
        navigation_count = 0
        for line in lines:
            if "NavigationManager.handle_navigation" in line:
                navigation_count += 1
        
        if navigation_count > 0:
            print(f"\n⚠️ SafeConversationHandler在fallback中添加了{navigation_count}次导航处理器")
            issues.append("SafeConversationHandler重复添加导航处理器")
    
    return issues


def check_premium_handler_v2():
    """检查Premium V2 handler实现"""
    print("\n=== 3. Premium V2 Handler分析 ===")
    print("-" * 40)
    
    handler_file = Path(__file__).parent.parent / "src" / "premium" / "handler_v2.py"
    with open(handler_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = []
    
    # 检查状态定义
    if "SELECTING_TARGET," in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "SELECTING_TARGET," in line:
                # 找到状态定义部分
                for j in range(i, min(len(lines), i+10)):
                    if ") = range(" in lines[j]:
                        state_count = lines[j].split("range(")[1].split(")")[0]
                        print(f"✓ 定义了{state_count}个状态")
                        break
    
    # 检查AWAITING_USERNAME_ACTION是否正确处理
    if "AWAITING_USERNAME_ACTION" in content:
        print("✓ 已添加AWAITING_USERNAME_ACTION状态")
        
        # 检查是否有对应的处理器
        if "CallbackQueryHandler(self.retry_username_action" in content:
            print("✓ 已添加retry_username_action处理器")
        else:
            print("✗ 缺少retry_username_action处理器")
            issues.append("缺少retry_username_action处理器")
    
    # 检查NavigationManager使用
    nav_count = content.count("NavigationManager.create_back_button")
    if nav_count > 0:
        print(f"✓ 使用了{nav_count}次NavigationManager.create_back_button")
    
    # 检查auto_bind_on_interaction
    if "auto_bind_on_interaction" in content:
        print("⚠️ 调用了auto_bind_on_interaction，可能引起数据库错误")
        issues.append("auto_bind_on_interaction可能有数据库问题")
    
    return issues


def check_navigation_conflicts():
    """检查导航冲突"""
    print("\n=== 4. 导航冲突分析 ===")
    print("-" * 40)
    
    issues = []
    
    print("可能的冲突点:")
    print("1. NavigationManager在group=0全局注册")
    print("2. SafeConversationHandler在fallback中也添加导航处理")
    print("3. 两者都会响应'back_to_main'等callback")
    print("\n结果: 返回按钮可能被处理两次")
    
    issues.append("导航处理器重复注册导致双重处理")
    
    return issues


def generate_fix_plan(all_issues: List[str]) -> Dict[str, Any]:
    """生成修复方案"""
    print("\n" + "="*60)
    print("📋 问题汇总与修复方案")
    print("="*60)
    
    fix_plan = {
        "issues": all_issues,
        "fixes": []
    }
    
    if "导航处理器重复注册导致双重处理" in all_issues:
        fix_plan["fixes"].append({
            "issue": "返回按钮重复执行",
            "severity": "高",
            "solution": """
1. 修改SafeConversationHandler，不在fallback中添加导航处理器
2. 或者修改bot.py，不要全局注册NavigationManager（推荐）
3. 让每个ConversationHandler自己管理导航
            """,
            "files": [
                "src/common/conversation_wrapper.py",
                "src/bot.py"
            ]
        })
    
    if "auto_bind_on_interaction可能有数据库问题" in all_issues:
        fix_plan["fixes"].append({
            "issue": "Premium点击报错",
            "severity": "高", 
            "solution": """
1. 优化auto_bind_on_interaction，使用db_manager上下文管理器
2. 添加更完善的错误处理
3. 避免在对话开始时就执行数据库操作
            """,
            "files": [
                "src/premium/user_verification.py",
                "src/premium/handler_v2.py"
            ]
        })
    
    if "SafeConversationHandler重复添加导航处理器" in all_issues:
        fix_plan["fixes"].append({
            "issue": "对话包装器配置问题",
            "severity": "中",
            "solution": """
1. 移除SafeConversationHandler中的导航处理器添加逻辑
2. 让导航完全由全局处理器管理
3. 或者完全移除全局导航，每个对话自己管理
            """,
            "files": [
                "src/common/conversation_wrapper.py"
            ]
        })
    
    return fix_plan


def main():
    """主函数"""
    print("🔍 Premium V2 问题诊断")
    print("="*60)
    
    all_issues = []
    
    # 1. 检查handler注册
    issues = check_handler_registration()
    all_issues.extend(issues)
    
    # 2. 检查SafeConversationHandler
    issues = check_conversation_wrapper()
    all_issues.extend(issues)
    
    # 3. 检查Premium handler
    issues = check_premium_handler_v2()
    all_issues.extend(issues)
    
    # 4. 检查导航冲突
    issues = check_navigation_conflicts()
    all_issues.extend(issues)
    
    # 5. 生成修复方案
    fix_plan = generate_fix_plan(all_issues)
    
    # 输出修复方案
    print("\n📝 修复方案详情:")
    print("-"*60)
    for i, fix in enumerate(fix_plan["fixes"], 1):
        print(f"\n{i}. {fix['issue']} (严重程度: {fix['severity']})")
        print(f"   解决方案:{fix['solution']}")
        print(f"   涉及文件: {', '.join(fix['files'])}")
    
    print("\n" + "="*60)
    print("✅ 诊断完成")
    print(f"发现{len(all_issues)}个问题，生成{len(fix_plan['fixes'])}个修复方案")
    

if __name__ == "__main__":
    main()
