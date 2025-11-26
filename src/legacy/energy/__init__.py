"""
Legacy Energy 模块 - 能量服务旧版实现

本模块为 V1 版本的能量服务业务逻辑，仅用于兼容。
后续会被 services/energy_service.py 封装替代。

包含：
- manager.py: 能量管理器
- client.py: 外部 API 客户端
- models.py: 数据模型
"""

from .manager import EnergyOrderManager
from .client import EnergyAPIClient, EnergyAPIError
from .models import EnergyOrder, EnergyOrderType, EnergyPackage, EnergyOrderStatus
