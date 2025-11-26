"""
Services 层 - 业务逻辑服务接口

本目录提供纯业务逻辑服务，供 modules/ 和 api/ 调用。
服务层不依赖 Telegram 类型（Update, CallbackQuery 等），
只接受业务参数，返回业务结果。

包含服务：
- payment_service: 支付相关操作
- wallet_service: 钱包余额管理
- energy_service: 能量服务操作
- trx_service: TRX 兑换操作
- address_service: 地址验证和查询
- config_service: 配置管理
"""

from .payment_service import PaymentService
from .wallet_service import WalletService
from .energy_service import EnergyService
from .trx_service import TRXService
from .address_service import AddressService
from .config_service import ConfigService

__all__ = [
    "PaymentService",
    "WalletService",
    "EnergyService",
    "TRXService",
    "AddressService",
    "ConfigService",
]
