"""
Legacy Address Query 模块 - 地址查询旧版实现

本模块为 V1 版本的地址查询业务逻辑，仅用于兼容。
后续会被 services/address_service.py 封装替代。

包含：
- validator.py: 波场地址验证
- explorer.py: 区块浏览器链接
"""

from .validator import validate_tron_address
from .explorer import get_tronscan_link
