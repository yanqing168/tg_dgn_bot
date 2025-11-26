"""
统一消息格式化器
处理所有消息的格式化和特殊字符转义
"""

from typing import Optional, Dict, Any


class MessageFormatter:
    """统一消息格式化器"""
    
    FORMAT_HTML = 'HTML'
    FORMAT_MARKDOWN = 'Markdown'
    FORMAT_MARKDOWN_V2 = 'MarkdownV2'
    
    @staticmethod
    def format_html(template: str, **kwargs) -> str:
        """
        格式化HTML消息
        
        Args:
            template: 消息模板，使用{key}作为占位符
            **kwargs: 模板参数
            
        Returns:
            格式化后的HTML消息，所有参数都会被自动转义
        """
        # 自动转义所有参数
        safe_kwargs = {
            k: MessageFormatter.escape_html(str(v)) if v is not None else ""
            for k, v in kwargs.items()
        }
        return template.format(**safe_kwargs)
    
    @staticmethod
    def escape_html(text: str) -> str:
        """
        HTML特殊字符转义
        
        Args:
            text: 需要转义的文本
            
        Returns:
            转义后的文本
        """
        if not text:
            return ""
            
        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Markdown V1特殊字符转义
        
        Args:
            text: 需要转义的文本
            
        Returns:
            转义后的文本
        """
        if not text:
            return ""
            
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    
    @staticmethod
    def escape_markdown_v2(text: str) -> str:
        """
        Markdown V2特殊字符转义
        
        Args:
            text: 需要转义的文本
            
        Returns:
            转义后的文本
        """
        if not text:
            return ""
            
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!', '\\']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    
    @staticmethod
    def safe_username(username: Optional[str], format_type: str = FORMAT_HTML) -> str:
        """
        安全格式化用户名
        
        Args:
            username: Telegram用户名
            format_type: 格式类型
            
        Returns:
            格式化后的用户名
        """
        if not username:
            return "未设置"
        
        if format_type == MessageFormatter.FORMAT_HTML:
            return f"@{MessageFormatter.escape_html(username)}"
        elif format_type == MessageFormatter.FORMAT_MARKDOWN:
            return f"@{MessageFormatter.escape_markdown(username)}"
        elif format_type == MessageFormatter.FORMAT_MARKDOWN_V2:
            return f"@{MessageFormatter.escape_markdown_v2(username)}"
        else:
            return f"@{username}"
    
    @staticmethod
    def safe_nickname(nickname: Optional[str], format_type: str = FORMAT_HTML) -> str:
        """
        安全格式化昵称
        
        Args:
            nickname: 用户昵称
            format_type: 格式类型
            
        Returns:
            格式化后的昵称
        """
        if not nickname:
            return "未知"
        
        if format_type == MessageFormatter.FORMAT_HTML:
            return MessageFormatter.escape_html(nickname)
        elif format_type == MessageFormatter.FORMAT_MARKDOWN:
            return MessageFormatter.escape_markdown(nickname)
        elif format_type == MessageFormatter.FORMAT_MARKDOWN_V2:
            return MessageFormatter.escape_markdown_v2(nickname)
        else:
            return nickname
