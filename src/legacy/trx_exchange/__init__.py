"""
Legacy TRX Exchange 模块 - TRX 兑换旧版实现

本模块为 V1 版本的 TRX 兑换业务逻辑，仅用于兼容。
后续会被 services/trx_service.py 封装替代。

包含：
- config.py: 兑换配置
- rate_manager.py: 汇率管理
- trx_sender.py: TRX 发送器
"""

from .config import TRXExchangeConfig
from .rate_manager import RateManager
from .trx_sender import TRXSender
