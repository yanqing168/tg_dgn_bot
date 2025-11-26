"""
模块基类定义
所有标准化模块都应继承此基类
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from telegram.ext import BaseHandler


class BaseModule(ABC):
    """所有模块的基类"""
    
    @abstractmethod
    def get_handlers(self) -> List[BaseHandler]:
        """
        获取模块的所有处理器
        
        Returns:
            处理器列表，将被注册到Application
        """
        pass
    
    @property
    @abstractmethod
    def module_name(self) -> str:
        """
        模块名称
        
        Returns:
            模块的唯一标识符
        """
        pass
    
    def validate_config(self) -> bool:
        """
        验证模块配置
        
        Returns:
            配置是否有效
        """
        return True
    
    def on_startup(self) -> None:
        """模块启动时的初始化操作"""
        pass
    
    def on_shutdown(self) -> None:
        """模块关闭时的清理操作"""
        pass
