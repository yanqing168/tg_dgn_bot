"""
波场地址验证器

[Legacy] 旧版实现，仅用于兼容，后续会被 services 层封装替代
"""
import re
from typing import Optional, Tuple


class AddressValidator:
    """波场地址验证器"""
    
    @staticmethod
    def validate(address: str) -> Tuple[bool, Optional[str]]:
        """
        验证波场地址格式
        
        Args:
            address: 待验证的地址
            
        Returns:
            (是否有效, 错误消息)
        """
        if not address:
            return False, "地址不能为空"
        
        # 检查是否以 T 开头
        if not address.startswith('T'):
            return False, "波场地址必须以 'T' 开头"
        
        # 检查长度
        if len(address) != 34:
            return False, f"地址长度错误（应为 34 位，实际 {len(address)} 位）"
        
        # 检查字符集（Base58: 不包含 0OIl）
        base58_pattern = r'^T[A-HJ-NP-Za-km-z1-9]{33}$'
        if not re.match(base58_pattern, address):
            return False, "地址包含无效字符（仅支持 Base58 字符集）"
        
        return True, None


def validate_tron_address(address: str) -> Tuple[bool, Optional[str]]:
    """
    验证波场地址格式（便捷函数）
    
    Args:
        address: 待验证的地址
        
    Returns:
        (是否有效, 错误消息)
    """
    return AddressValidator.validate(address)
