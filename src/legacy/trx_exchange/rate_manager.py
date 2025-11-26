"""TRX Exchange Rate Manager - Fixed Rate with Admin Control.

[Legacy] 旧版实现，仅用于兼容，后续会被 services 层封装替代

注意：为避免类重复定义和缓存不一致问题，
RateManager 和 TRXExchangeRate 都从原始位置导入。
"""

# 直接从原始位置导入，避免类重复定义
from ...trx_exchange.rate_manager import RateManager, TRXExchangeRate

# 同时导出 config（保持兼容）
from .config import TRXExchangeConfig

__all__ = ["RateManager", "TRXExchangeRate", "TRXExchangeConfig"]
