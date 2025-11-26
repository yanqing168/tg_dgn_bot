"""
地址查询模块

[架构说明]
- 业务逻辑类（validator, explorer）已迁移到 src/legacy/address_query/
- 本目录保留 Telegram handler（handler.py）
- 为保持兼容，通过本 __init__.py 重新导出 legacy 中的类
"""

from .handler import AddressQueryHandler

# 从 legacy 导入业务逻辑类（保持兼容）
from ..legacy.address_query.validator import AddressValidator, validate_tron_address
from ..legacy.address_query.explorer import explorer_links, get_tronscan_link

__all__ = [
    # Telegram handler
    'AddressQueryHandler',
    # 业务逻辑类（从 legacy 导入）
    'AddressValidator',
    'validate_tron_address',
    'explorer_links',
    'get_tronscan_link',
]
