"""
核心基础设施模块
提供标准化模块改造的基础组件
"""

from .base import BaseModule
from .formatter import MessageFormatter
from .state_manager import ModuleStateManager
from .registry import ModuleRegistry, get_registry

__all__ = [
    'BaseModule',
    'MessageFormatter',
    'ModuleStateManager',
    'ModuleRegistry',
    'get_registry'
]
