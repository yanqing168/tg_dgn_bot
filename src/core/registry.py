"""
模块注册中心 - 统一管理所有Bot模块
"""

import logging
from typing import Dict, List, Optional, Any
from telegram.ext import BaseHandler, Application

from .base import BaseModule


logger = logging.getLogger(__name__)


class ModuleRegistry:
    """模块注册中心"""
    
    def __init__(self):
        """初始化注册中心"""
        self._modules: Dict[str, BaseModule] = {}
        self._module_info: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    def register(self, module: BaseModule, 
                 priority: int = 5,
                 enabled: bool = True,
                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        注册模块
        
        Args:
            module: 模块实例
            priority: 优先级（0-10，数字越小优先级越高）
            enabled: 是否启用
            metadata: 模块元数据
        """
        module_name = module.module_name
        
        if module_name in self._modules:
            logger.warning(f"模块 {module_name} 已存在，将被覆盖")
        
        self._modules[module_name] = module
        self._module_info[module_name] = {
            'priority': priority,
            'enabled': enabled,
            'metadata': metadata or {},
            'handlers_count': 0
        }
        
        logger.info(f"✅ 注册模块: {module_name} (优先级={priority}, 启用={enabled})")
    
    def unregister(self, module_name: str) -> bool:
        """
        注销模块
        
        Args:
            module_name: 模块名称
            
        Returns:
            是否成功注销
        """
        if module_name in self._modules:
            del self._modules[module_name]
            del self._module_info[module_name]
            logger.info(f"✅ 注销模块: {module_name}")
            return True
        return False
    
    def get_module(self, module_name: str) -> Optional[BaseModule]:
        """获取模块实例"""
        return self._modules.get(module_name)
    
    def list_modules(self) -> List[str]:
        """列出所有已注册的模块"""
        return list(self._modules.keys())
    
    def get_module_info(self, module_name: str) -> Optional[Dict[str, Any]]:
        """获取模块信息"""
        return self._module_info.get(module_name)
    
    def is_enabled(self, module_name: str) -> bool:
        """检查模块是否启用"""
        info = self._module_info.get(module_name, {})
        return info.get('enabled', False)
    
    def enable_module(self, module_name: str) -> bool:
        """启用模块"""
        if module_name in self._module_info:
            self._module_info[module_name]['enabled'] = True
            logger.info(f"✅ 启用模块: {module_name}")
            return True
        return False
    
    def disable_module(self, module_name: str) -> bool:
        """禁用模块"""
        if module_name in self._module_info:
            self._module_info[module_name]['enabled'] = False
            logger.info(f"⏸️ 禁用模块: {module_name}")
            return True
        return False
    
    def initialize_all(self, app: Application) -> None:
        """
        初始化所有模块并注册处理器
        
        Args:
            app: Telegram Application 实例
        """
        if self._initialized:
            logger.warning("模块已初始化，跳过重复初始化")
            return
        
        # 按优先级排序模块
        sorted_modules = sorted(
            self._modules.items(),
            key=lambda x: self._module_info[x[0]]['priority']
        )
        
        for module_name, module in sorted_modules:
            info = self._module_info[module_name]
            
            if not info['enabled']:
                logger.info(f"⏭️ 跳过禁用的模块: {module_name}")
                continue
            
            try:
                # 获取模块处理器
                handlers = module.get_handlers()
                priority = info['priority']
                
                # 注册处理器
                for handler in handlers:
                    app.add_handler(handler, group=priority)
                    info['handlers_count'] += 1
                
                logger.info(
                    f"✅ 模块 {module_name} 已初始化: "
                    f"{info['handlers_count']} 个处理器 (group={priority})"
                )
                
            except Exception as e:
                logger.error(f"❌ 初始化模块 {module_name} 失败: {e}")
                info['enabled'] = False
        
        self._initialized = True
        logger.info(f"🎯 共初始化 {len([m for m in self._module_info.values() if m['enabled']])} 个模块")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取注册中心统计信息"""
        enabled_count = sum(1 for info in self._module_info.values() if info['enabled'])
        total_handlers = sum(info['handlers_count'] for info in self._module_info.values())
        
        return {
            'total_modules': len(self._modules),
            'enabled_modules': enabled_count,
            'disabled_modules': len(self._modules) - enabled_count,
            'total_handlers': total_handlers,
            'modules': {
                name: {
                    'enabled': info['enabled'],
                    'priority': info['priority'],
                    'handlers': info['handlers_count']
                }
                for name, info in self._module_info.items()
            }
        }


# 全局注册中心实例
module_registry = ModuleRegistry()


def get_registry() -> ModuleRegistry:
    """获取全局注册中心实例"""
    return module_registry
