#!/usr/bin/env python3
"""
Bot全面诊断脚本
检查所有可能的生产环境问题
"""
import sys
import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BotDiagnostic:
    """Bot诊断类"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.suggestions = []
        self.root_dir = Path(__file__).parent.parent
        
    def run_diagnostic(self) -> Dict[str, Any]:
        """运行完整诊断"""
        print("\n" + "="*60)
        print(" "*20 + "Bot系统诊断")
        print("="*60)
        
        # 1. 检查配置问题
        self._check_configuration()
        
        # 2. 检查安全问题
        self._check_security()
        
        # 3. 检查代码问题
        self._check_code_issues()
        
        # 4. 检查数据库问题
        self._check_database()
        
        # 5. 检查错误处理
        self._check_error_handling()
        
        # 6. 检查性能问题
        self._check_performance()
        
        # 7. 检查导航问题
        self._check_navigation_issues()
        
        # 8. 检查Premium V2特定问题
        self._check_premium_v2_issues()
        
        return self._generate_report()
    
    def _check_configuration(self):
        """检查配置问题"""
        print("\n[1/8] 检查配置...")
        
        # 检查.env文件
        env_file = self.root_dir / '.env'
        if not env_file.exists():
            self.issues.append(("配置", "缺少.env文件", "高"))
        else:
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查必要配置
                required_configs = [
                    'BOT_TOKEN',
                    'BOT_OWNER_ID',
                    'USDT_TRC20_RECEIVE_ADDR',
                    'DATABASE_URL',
                    'REDIS_HOST'
                ]
                
                for config in required_configs:
                    if config not in content:
                        self.issues.append(("配置", f"缺少必要配置: {config}", "高"))
                
                # 检查敏感信息
                if 'BOT_TOKEN=' in content and len(content.split('BOT_TOKEN=')[1].split('\n')[0]) > 10:
                    self.warnings.append(("配置", "BOT_TOKEN暴露在配置中", "中"))
        
        print(f"  发现 {len([i for i in self.issues if i[0] == '配置'])} 个配置问题")
    
    def _check_security(self):
        """检查安全问题"""
        print("\n[2/8] 检查安全...")
        
        # 检查SQL注入风险
        src_dir = self.root_dir / 'src'
        for py_file in src_dir.rglob('*.py'):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查直接字符串拼接SQL
                if 'execute(f"' in content or 'execute("' in content:
                    if '.format(' in content or 'f"SELECT' in content:
                        self.issues.append((
                            "安全",
                            f"潜在SQL注入风险: {py_file.relative_to(self.root_dir)}",
                            "高"
                        ))
                
                # 检查硬编码密钥
                if re.search(r'(api_key|secret|password)\s*=\s*["\'][^"\']+["\']', content, re.IGNORECASE):
                    self.warnings.append((
                        "安全",
                        f"硬编码密钥: {py_file.relative_to(self.root_dir)}",
                        "中"
                    ))
        
        # 检查输入验证
        handler_files = list((self.root_dir / 'src').rglob('*handler*.py'))
        for handler_file in handler_files:
            with open(handler_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查是否有输入验证
                if 'update.message.text' in content:
                    if not ('validate' in content or 'strip()' in content or 'RecipientParser' in content):
                        self.warnings.append((
                            "安全",
                            f"缺少输入验证: {handler_file.relative_to(self.root_dir)}",
                            "中"
                        ))
        
        print(f"  发现 {len([i for i in self.issues if i[0] == '安全'])} 个安全问题")
    
    def _check_code_issues(self):
        """检查代码问题"""
        print("\n[3/8] 检查代码质量...")
        
        # 检查未处理的异常
        src_dir = self.root_dir / 'src'
        for py_file in src_dir.rglob('*.py'):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查裸露的except
                if re.search(r'except:\s*\n\s*(pass|continue)', content):
                    self.warnings.append((
                        "代码",
                        f"裸露except: {py_file.relative_to(self.root_dir)}",
                        "低"
                    ))
                
                # 检查TODO和FIXME
                if 'TODO' in content or 'FIXME' in content:
                    self.warnings.append((
                        "代码",
                        f"未完成代码: {py_file.relative_to(self.root_dir)}",
                        "低"
                    ))
        
        print(f"  发现 {len([i for i in self.warnings if i[0] == '代码'])} 个代码质量问题")
    
    def _check_database(self):
        """检查数据库问题"""
        print("\n[4/8] 检查数据库...")
        
        # 检查数据库连接泄露
        src_dir = self.root_dir / 'src'
        for py_file in src_dir.rglob('*.py'):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查是否有正确关闭数据库
                if 'get_db()' in content:
                    if 'finally:' not in content or 'close_db' not in content:
                        self.warnings.append((
                            "数据库",
                            f"可能的数据库连接泄露: {py_file.relative_to(self.root_dir)}",
                            "高"
                        ))
        
        print(f"  发现 {len([i for i in self.warnings if i[0] == '数据库'])} 个数据库问题")
    
    def _check_error_handling(self):
        """检查错误处理"""
        print("\n[5/8] 检查错误处理...")
        
        # 检查error_handler装饰器的使用
        handler_files = list((self.root_dir / 'src').rglob('*handler*.py'))
        for handler_file in handler_files:
            with open(handler_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 统计async def方法
                async_methods = len(re.findall(r'async def \w+', content))
                
                # 统计@error_handler
                error_handlers = len(re.findall(r'@error_handler', content))
                
                if async_methods > 0 and error_handlers < async_methods * 0.5:
                    self.warnings.append((
                        "错误处理",
                        f"错误处理覆盖不足: {handler_file.relative_to(self.root_dir)}",
                        "中"
                    ))
        
        print(f"  发现 {len([i for i in self.warnings if i[0] == '错误处理'])} 个错误处理问题")
    
    def _check_performance(self):
        """检查性能问题"""
        print("\n[6/8] 检查性能...")
        
        # 检查N+1查询
        src_dir = self.root_dir / 'src'
        for py_file in src_dir.rglob('*.py'):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查循环中的数据库查询
                if re.search(r'for .+ in .+:\s*\n.*query\(', content, re.MULTILINE):
                    self.warnings.append((
                        "性能",
                        f"可能的N+1查询: {py_file.relative_to(self.root_dir)}",
                        "中"
                    ))
        
        print(f"  发现 {len([i for i in self.warnings if i[0] == '性能'])} 个性能问题")
    
    def _check_navigation_issues(self):
        """检查导航系统问题"""
        print("\n[7/8] 检查导航系统...")
        
        # 检查Premium V2的导航问题
        premium_v2_file = self.root_dir / 'src' / 'premium' / 'handler_v2.py'
        if premium_v2_file.exists():
            with open(premium_v2_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 问题1: retry_user后返回ENTERING_USERNAME但用户在inline界面
                if 'retry_user' in content and 'ENTERING_USERNAME' in content:
                    self.issues.append((
                        "导航",
                        "Premium V2: retry_user后状态不一致",
                        "高"
                    ))
                
                # 问题2: 用户验证失败后的导航
                if 'not result[\'exists\']' in content:
                    # 检查是否正确处理
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'not result[\'exists\']' in line:
                            # 检查后续几行
                            next_lines = '\n'.join(lines[i:i+20])
                            if 'ENTERING_USERNAME' in next_lines and 'InlineKeyboard' in next_lines:
                                self.issues.append((
                                    "导航",
                                    "Premium V2: 用户验证失败后界面状态不匹配",
                                    "高"
                                ))
        
        print(f"  发现 {len([i for i in self.issues if i[0] == '导航'])} 个导航问题")
    
    def _check_premium_v2_issues(self):
        """检查Premium V2特定问题"""
        print("\n[8/8] 检查Premium V2...")
        
        premium_v2_file = self.root_dir / 'src' / 'premium' / 'handler_v2.py'
        if premium_v2_file.exists():
            with open(premium_v2_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 问题1: username_entered中的状态返回问题
                if 'def username_entered' in content:
                    method_content = self._extract_method(content, 'username_entered')
                    if 'return ENTERING_USERNAME' in method_content and 'InlineKeyboardMarkup' in method_content:
                        self.issues.append((
                            "Premium V2",
                            "username_entered: 返回文本输入状态但提供了inline键盘",
                            "高"
                        ))
                
                # 问题2: 用户名解析问题
                if 'RecipientParser.parse' in content:
                    # parse方法的正则表达式只匹配3-32字符，但验证需要5-32
                    self.issues.append((
                        "Premium V2",
                        "RecipientParser: 解析和验证的正则不一致（3-32 vs 5-32）",
                        "中"
                    ))
                
                # 问题3: 错误处理覆盖
                error_handlers = len(re.findall(r'@error_handler', content))
                async_methods = len(re.findall(r'async def \w+', content))
                if error_handlers < async_methods - 2:  # 允许一些辅助方法没有装饰器
                    self.warnings.append((
                        "Premium V2",
                        f"错误处理覆盖不足: {error_handlers}/{async_methods}",
                        "中"
                    ))
        
        print(f"  发现 {len([i for i in self.issues if i[0] == 'Premium V2'])} 个Premium V2问题")
    
    def _extract_method(self, content: str, method_name: str) -> str:
        """提取方法内容"""
        lines = content.split('\n')
        start_idx = -1
        
        for i, line in enumerate(lines):
            if f'def {method_name}' in line:
                start_idx = i
                break
        
        if start_idx == -1:
            return ""
        
        # 找到下一个def或class
        end_idx = len(lines)
        indent_level = len(lines[start_idx]) - len(lines[start_idx].lstrip())
        
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if line.strip() and not line.startswith(' ' * (indent_level + 1)):
                if line.strip().startswith('def ') or line.strip().startswith('class '):
                    end_idx = i
                    break
        
        return '\n'.join(lines[start_idx:end_idx])
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成诊断报告"""
        print("\n" + "="*60)
        print(" "*20 + "诊断报告")
        print("="*60)
        
        # 统计
        total_issues = len(self.issues)
        total_warnings = len(self.warnings)
        
        # 按严重程度分类
        high_priority = [i for i in self.issues if i[2] == "高"]
        medium_priority = [i for i in self.issues if i[2] == "中"] + \
                         [w for w in self.warnings if w[2] == "中"]
        low_priority = [i for i in self.issues if i[2] == "低"] + \
                      [w for w in self.warnings if w[2] == "低"]
        
        print(f"\n📊 统计:")
        print(f"  严重问题: {len(high_priority)}")
        print(f"  中等问题: {len(medium_priority)}")
        print(f"  轻微问题: {len(low_priority)}")
        print(f"  总计: {total_issues + total_warnings}")
        
        # 严重问题详情
        if high_priority:
            print(f"\n🔴 严重问题 ({len(high_priority)}):")
            for category, desc, _ in high_priority:
                print(f"  [{category}] {desc}")
        
        # 中等问题详情
        if medium_priority:
            print(f"\n🟡 中等问题 ({len(medium_priority)}):")
            for category, desc, _ in medium_priority[:5]:  # 只显示前5个
                print(f"  [{category}] {desc}")
            if len(medium_priority) > 5:
                print(f"  ... 还有 {len(medium_priority) - 5} 个中等问题")
        
        # 建议
        print("\n💡 修复建议:")
        suggestions = self._generate_suggestions()
        for i, suggestion in enumerate(suggestions[:5], 1):
            print(f"  {i}. {suggestion}")
        
        return {
            "issues": self.issues,
            "warnings": self.warnings,
            "suggestions": suggestions,
            "summary": {
                "high": len(high_priority),
                "medium": len(medium_priority),
                "low": len(low_priority),
                "total": total_issues + total_warnings
            }
        }
    
    def _generate_suggestions(self) -> List[str]:
        """生成修复建议"""
        suggestions = []
        
        # 基于发现的问题生成建议
        for issue in self.issues:
            category, desc, priority = issue
            
            if "Premium V2" in category and "状态" in desc:
                suggestions.append("修复Premium V2的状态机：retry_user应该发送新消息而不是编辑")
            
            if "导航" in category:
                suggestions.append("统一处理所有ConversationHandler的返回状态")
            
            if "数据库" in category and "连接泄露" in desc:
                suggestions.append("使用context manager确保数据库连接正确关闭")
            
            if "RecipientParser" in desc:
                suggestions.append("统一RecipientParser的解析和验证正则表达式")
        
        # 通用建议
        if len(self.issues) > 5:
            suggestions.append("建立完整的错误监控和日志系统")
            suggestions.append("增加单元测试覆盖率")
            suggestions.append("实施代码审查流程")
        
        return list(set(suggestions))  # 去重


if __name__ == "__main__":
    diagnostic = BotDiagnostic()
    report = diagnostic.run_diagnostic()
    
    # 生成JSON报告
    report_file = Path(__file__).parent.parent / 'diagnostic_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细报告已保存到: {report_file}")
    
    # 返回码
    if report['summary']['high'] > 0:
        print("\n❌ 发现严重问题，请立即修复！")
        sys.exit(1)
    elif report['summary']['medium'] > 0:
        print("\n⚠️ 发现中等问题，建议尽快修复")
        sys.exit(0)
    else:
        print("\n✅ 未发现严重问题")
        sys.exit(0)
