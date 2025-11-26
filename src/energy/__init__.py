"""
能量兑换模块
提供 TRON 能量租用、笔数套餐、闪兑功能

注意：当前使用 handler_direct.py 中的 EnergyDirectHandler（直转模式）
     handler.py 中的 EnergyHandler（余额模式）已废弃，不再导出

[架构说明]
- 业务逻辑类（models, client, manager）已迁移到 src/legacy/energy/
- 本目录保留 Telegram handler（handler.py, handler_direct.py）
- 为保持兼容，通过本 __init__.py 重新导出 legacy 中的类
"""

# 从 legacy 导入业务逻辑类（保持兼容）
from ..legacy.energy.client import EnergyAPIClient, EnergyAPIError
from ..legacy.energy.models import (
    EnergyOrderType,
    EnergyPackage,
    EnergyOrderStatus,
    EnergyOrder,
    EnergyPriceConfig,
    APIAccountInfo,
    APIPriceQuery,
    APIOrderResponse,
)
from ..legacy.energy.manager import EnergyOrderManager

__all__ = [
    # 业务逻辑类（从 legacy 导入）
    "EnergyAPIClient",
    "EnergyAPIError",
    "EnergyOrderType",
    "EnergyPackage",
    "EnergyOrderStatus",
    "EnergyOrder",
    "EnergyPriceConfig",
    "APIAccountInfo",
    "APIPriceQuery",
    "APIOrderResponse",
    "EnergyOrderManager",
]
