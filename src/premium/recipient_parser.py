"""
收件人解析器：处理用户名、链接、去重和规范化
"""
import re
from typing import List, Set


class RecipientParser:
    """解析和验证 Premium 收件人"""
    
    # 正则表达式（统一为5-32字符，符合Telegram规范）
    USERNAME_PATTERN = re.compile(r'@([a-zA-Z0-9_]{5,32})(?![a-zA-Z0-9_])')
    TGLINK_PATTERN = re.compile(r't\.me/([a-zA-Z0-9_]{5,32})(?![a-zA-Z0-9_])')
    
    @classmethod
    def parse(cls, text: str) -> List[str]:
        """
        从文本中解析收件人用户名
        
        Args:
            text: 包含用户名或链接的文本
            
        Returns:
            去重且规范化的用户名列表
        """
        usernames: Set[str] = set()
        
        # 解析 @username 格式
        for match in cls.USERNAME_PATTERN.finditer(text):
            usernames.add(match.group(1).lower())
        
        # 解析 t.me/username 格式
        for match in cls.TGLINK_PATTERN.finditer(text):
            usernames.add(match.group(1).lower())
        
        return sorted(usernames)  # 排序确保一致性
    
    @classmethod
    def validate_username(cls, username: str) -> bool:
        """
        验证用户名格式
        
        Args:
            username: Telegram用户名（不含@）
            
        Returns:
            是否有效
        """
        # Telegram用户名规则：5-32字符，字母、数字、下划线
        pattern = re.compile(r'^[a-zA-Z0-9_]{5,32}$')
        return bool(pattern.match(username))
    
    @classmethod
    def normalize(cls, username: str) -> str:
        """
        规范化用户名（移除@，转小写）
        
        Args:
            username: 原始用户名
            
        Returns:
            规范化后的用户名
        """
        username = username.strip()
        if username.startswith('@'):
            username = username[1:]
        return username.lower()
