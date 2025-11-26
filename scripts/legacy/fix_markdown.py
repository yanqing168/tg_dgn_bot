#!/usr/bin/env python3
"""
Markdown 格式修复脚本
自动修复常见的 Markdown lint 错误
"""

import re
from pathlib import Path


def fix_markdown_format(content: str) -> str:
    """修复 Markdown 格式问题"""
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        prev_line = lines[i-1] if i > 0 else ''
        next_line = lines[i+1] if i < len(lines) - 1 else ''
        
        # 1. 修复标题前后空行 (MD022)
        if line.startswith('#'):
            # 标题前需要空行（除非是文件开头）
            if i > 0 and prev_line.strip() != '':
                fixed_lines.append('')
            fixed_lines.append(line)
            # 标题后需要空行（除非后面已经有空行）
            if next_line.strip() != '':
                fixed_lines.append('')
            i += 1
            continue
        
        # 2. 修复列表前后空行 (MD032)
        if line.startswith('- ') or line.startswith('* ') or re.match(r'^\d+\. ', line):
            # 列表前需要空行
            if i > 0 and prev_line.strip() != '' and not prev_line.startswith(('-', '*', '  ')):
                fixed_lines.append('')
            fixed_lines.append(line)
            # 收集整个列表
            j = i + 1
            while j < len(lines) and (lines[j].startswith(('-', '*', '  ')) or lines[j].strip() == ''):
                fixed_lines.append(lines[j])
                j += 1
            # 列表后需要空行
            if j < len(lines) and lines[j].strip() != '':
                fixed_lines.append('')
            i = j
            continue
        
        # 3. 修复代码块前后空行 (MD031)
        if line.strip().startswith('```'):
            # 代码块前需要空行
            if i > 0 and prev_line.strip() != '':
                fixed_lines.append('')
            
            # 修复代码块语言标识 (MD040)
            if line.strip() == '```':
                # 推测语言类型
                next_content = lines[i+1] if i < len(lines) - 1 else ''
                if 'def ' in next_content or 'import ' in next_content or 'class ' in next_content:
                    fixed_lines.append('```python')
                elif 'pytest' in next_content or '$ ' in next_content:
                    fixed_lines.append('```bash')
                elif '{' in next_content or '=' in next_content:
                    fixed_lines.append('```json')
                else:
                    fixed_lines.append('```text')
            else:
                fixed_lines.append(line)
            
            # 收集代码块内容
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith('```'):
                fixed_lines.append(lines[j])
                j += 1
            if j < len(lines):
                fixed_lines.append(lines[j])  # 结束标记
                # 代码块后需要空行
                if j + 1 < len(lines) and lines[j+1].strip() != '':
                    fixed_lines.append('')
            i = j + 1
            continue
        
        # 4. 修复粗体标题 (MD036)
        if line.strip().startswith('**') and line.strip().endswith('**') and len(line.strip()) < 100:
            # 转换为四级标题
            title = line.strip()[2:-2]
            if prev_line.strip() != '':
                fixed_lines.append('')
            fixed_lines.append(f'#### {title}')
            if next_line.strip() != '':
                fixed_lines.append('')
            i += 1
            continue
        
        # 默认保留原行
        fixed_lines.append(line)
        i += 1
    
    return '\n'.join(fixed_lines)


def main():
    """修复指定的 Markdown 文件"""
    files_to_fix = [
        'docs/STAGE1_SUMMARY.md',
        'docs/STAGE2_SUMMARY.md',
        'docs/CODE_REVIEW_STAGE1_2.md',
    ]
    
    for file_path in files_to_fix:
        path = Path(file_path)
        if not path.exists():
            print(f'⚠️  文件不存在: {file_path}')
            continue
        
        print(f'🔧 修复 {file_path}...')
        content = path.read_text(encoding='utf-8')
        fixed_content = fix_markdown_format(content)
        path.write_text(fixed_content, encoding='utf-8')
        print(f'✅ 完成 {file_path}')
    
    print('\n✨ 所有文档已修复！')


if __name__ == '__main__':
    main()
