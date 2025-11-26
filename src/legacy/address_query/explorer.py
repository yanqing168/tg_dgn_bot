"""
区块链浏览器链接生成器

[Legacy] 旧版实现，仅用于兼容，后续会被 services 层封装替代
"""
from typing import Dict
from ...config import settings


def explorer_links(address: str) -> Dict[str, str]:
    """
    生成浏览器链接
    
    Args:
        address: 波场地址
        
    Returns:
        包含 overview 和 txs 链接的字典
    """
    explorer = getattr(settings, 'tron_explorer', 'tronscan').lower()
    
    if explorer == 'oklink':
        base_url = "https://www.oklink.com/zh-hans/trx"
        return {
            "overview": f"{base_url}/address/{address}",
            "txs": f"{base_url}/address/{address}/transaction"
        }
    else:  # tronscan (default)
        base_url = "https://tronscan.org/#"
        return {
            "overview": f"{base_url}/address/{address}",
            "txs": f"{base_url}/address/{address}/transfers"
        }


def get_tronscan_link(address: str) -> str:
    """
    获取 TronScan 地址链接（便捷函数）
    
    Args:
        address: 波场地址
        
    Returns:
        TronScan 地址链接
    """
    return explorer_links(address)["overview"]
