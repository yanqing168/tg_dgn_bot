"""TRX Exchange Module - TRX/USDT Exchange with Fixed Rate.

[架构说明]
- 业务逻辑类（config, rate_manager, trx_sender）已迁移到 src/legacy/trx_exchange/
- 本目录保留 Telegram handler（handler.py）和 SQLAlchemy 模型（避免重复定义）
- 为保持兼容，通过本 __init__.py 重新导出类
"""

from .handler import TRXExchangeHandler
# TRXExchangeRate 模型保留在本模块，避免 SQLAlchemy 重复定义
from .rate_manager import TRXExchangeRate

# 从 legacy 导入业务逻辑类（保持兼容）
from ..legacy.trx_exchange.config import TRXExchangeConfig
from ..legacy.trx_exchange.rate_manager import RateManager
from ..legacy.trx_exchange.trx_sender import TRXSender

__all__ = [
    # Telegram handler
    "TRXExchangeHandler",
    # SQLAlchemy 模型
    "TRXExchangeRate",
    # 业务逻辑类（从 legacy 导入）
    "TRXExchangeConfig",
    "RateManager",
    "TRXSender",
]
