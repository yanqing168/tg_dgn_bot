#!/usr/bin/env python3
"""
修复所有cancel handler的update.message问题
确保同时支持message和callback_query
"""
import os
import re
from pathlib import Path
from typing import List, Tuple

def find_cancel_methods(root_dir: Path) -> List[Tuple[Path, int, str]]:
    """查找所有需要修复的cancel方法"""
    issues = []
    
    for py_file in root_dir.rglob('*.py'):
        if 'test' in str(py_file) or '__pycache__' in str(py_file):
            continue
            
        with open(py_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            # 查找可能有问题的cancel方法
            if 'def _cancel' in line or 'def cancel' in line:
                # 检查后续几行是否有update.message.reply_text
                for j in range(i, min(i+10, len(lines))):
                    if 'update.message.reply_text' in lines[j]:
                        # 检查是否已经有兼容处理
                        has_check = False
                        for k in range(i, j):
                            if 'if update.message' in lines[k] or 'update.effective_message' in lines[k]:
                                has_check = True
                                break
                        
                        if not has_check:
                            issues.append((py_file, j+1, lines[j].strip()))
                        break
    
    return issues

def generate_fix(file_path: Path, line_num: int) -> str:
    """生成修复代码"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到方法定义
    method_start = -1
    for i in range(line_num-1, max(0, line_num-20), -1):
        if 'async def' in lines[i] and 'cancel' in lines[i].lower():
            method_start = i
            break
    
    if method_start == -1:
        return None
    
    # 生成修复后的方法
    indent = len(lines[method_start]) - len(lines[method_start].lstrip())
    method_indent = ' ' * indent
    body_indent = ' ' * (indent + 4)
    
    fix_template = f'''
{method_indent}async def _cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
{body_indent}"""Cancel conversation - supports both message and callback_query."""
{body_indent}if update.callback_query:
{body_indent}    await update.callback_query.answer()
{body_indent}    await update.callback_query.edit_message_text("❌ 操作已取消")
{body_indent}elif update.message:
{body_indent}    await update.message.reply_text("❌ 操作已取消")
{body_indent}else:
{body_indent}    # Fallback for other update types
{body_indent}    if update.effective_message:
{body_indent}        await update.effective_message.reply_text("❌ 操作已取消")
{body_indent}
{body_indent}# Clear context data
{body_indent}context.user_data.clear()
{body_indent}
{body_indent}return ConversationHandler.END
'''
    
    return fix_template

def apply_fixes(root_dir: Path, dry_run: bool = True):
    """应用修复"""
    issues = find_cancel_methods(root_dir)
    
    print(f"发现 {len(issues)} 个需要修复的cancel方法")
    print("="*60)
    
    fixes_applied = []
    
    for file_path, line_num, line_content in issues:
        rel_path = file_path.relative_to(root_dir)
        print(f"\n📁 {rel_path}")
        print(f"   行 {line_num}: {line_content}")
        
        if not dry_run:
            # 这里可以实际应用修复
            fixes_applied.append(str(rel_path))
    
    return fixes_applied

def create_safe_cancel_handler() -> str:
    """创建一个安全的cancel handler模板"""
    return '''
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

async def safe_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    安全的取消处理器，同时支持message和callback_query
    
    使用方法:
        # 在ConversationHandler的fallbacks中
        CallbackQueryHandler(safe_cancel_handler, pattern="^cancel$"),
        CommandHandler("cancel", safe_cancel_handler),
    """
    # 清理用户数据
    context.user_data.clear()
    
    # 根据update类型发送响应
    if update.callback_query:
        # 处理按钮点击
        await update.callback_query.answer("已取消")
        
        # 尝试编辑消息
        try:
            await update.callback_query.edit_message_text(
                "❌ 操作已取消\\n\\n"
                "请选择其他功能或返回主菜单。"
            )
        except Exception:
            # 如果编辑失败（消息太旧或已编辑），发送新消息
            await update.effective_message.reply_text(
                "❌ 操作已取消\\n\\n"
                "请选择其他功能或返回主菜单。"
            )
    
    elif update.message:
        # 处理文本命令
        await update.message.reply_text(
            "❌ 操作已取消\\n\\n"
            "请选择其他功能或返回主菜单。"
        )
    
    else:
        # 其他类型的update（理论上不应该到这里）
        if update.effective_message:
            await update.effective_message.reply_text("❌ 操作已取消")
    
    return ConversationHandler.END
'''

if __name__ == "__main__":
    import sys
    
    # 设置项目根目录
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    
    print("🔍 扫描需要修复的cancel handlers...")
    print("="*60)
    
    # 只是扫描，不实际修复
    issues = find_cancel_methods(src_dir)
    
    if not issues:
        print("✅ 没有发现需要修复的cancel handler")
    else:
        print(f"\n发现 {len(issues)} 个潜在问题:")
        print("-"*60)
        
        for file_path, line_num, line_content in issues:
            rel_path = file_path.relative_to(project_root)
            print(f"📄 {rel_path}:{line_num}")
            print(f"   {line_content[:80]}...")
        
        print("\n" + "="*60)
        print("💡 建议修复方案:")
        print(create_safe_cancel_handler())
        
        print("\n⚠️ 这是一个dry run，没有实际修改文件")
        print("如需应用修复，请手动编辑相关文件")
