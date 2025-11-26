"""
模块状态管理器
统一管理各模块的状态数据
"""

from typing import Dict, Any, Optional
from telegram.ext import ContextTypes


class ModuleStateManager:
    """模块状态管理器"""
    
    # 需要保留的全局键（继承自NavigationManager）
    PRESERVED_KEYS = [
        'user_id', 
        'username', 
        'first_name', 
        'is_admin',
        'language', 
        'last_command', 
        'current_module',
        'main_menu_keyboard_shown'
    ]
    
    @staticmethod
    def init_state(context: ContextTypes.DEFAULT_TYPE, module_name: str) -> Dict[str, Any]:
        """
        初始化模块状态
        
        Args:
            context: Telegram context
            module_name: 模块名称
            
        Returns:
            模块状态字典
        """
        if 'modules' not in context.user_data:
            context.user_data['modules'] = {}
        
        if module_name not in context.user_data['modules']:
            context.user_data['modules'][module_name] = {}
        
        return context.user_data['modules'][module_name]
    
    @staticmethod
    def get_state(context: ContextTypes.DEFAULT_TYPE, module_name: str) -> Dict[str, Any]:
        """
        获取模块状态
        
        Args:
            context: Telegram context
            module_name: 模块名称
            
        Returns:
            模块状态字典，如果不存在返回空字典
        """
        return context.user_data.get('modules', {}).get(module_name, {})
    
    @staticmethod
    def set_state(context: ContextTypes.DEFAULT_TYPE, module_name: str, key: str, value: Any) -> None:
        """
        设置模块状态的某个值
        
        Args:
            context: Telegram context
            module_name: 模块名称
            key: 状态键
            value: 状态值
        """
        if 'modules' not in context.user_data:
            context.user_data['modules'] = {}
        
        if module_name not in context.user_data['modules']:
            context.user_data['modules'][module_name] = {}
        
        context.user_data['modules'][module_name][key] = value
    
    @staticmethod
    def get_value(context: ContextTypes.DEFAULT_TYPE, module_name: str, key: str, default: Any = None) -> Any:
        """
        获取模块状态的某个值
        
        Args:
            context: Telegram context
            module_name: 模块名称
            key: 状态键
            default: 默认值
            
        Returns:
            状态值，如果不存在返回默认值
        """
        return context.user_data.get('modules', {}).get(module_name, {}).get(key, default)
    
    @staticmethod
    def clear_state(context: ContextTypes.DEFAULT_TYPE, module_name: str) -> None:
        """
        清理模块状态
        
        Args:
            context: Telegram context
            module_name: 模块名称
        """
        if 'modules' in context.user_data and module_name in context.user_data['modules']:
            context.user_data['modules'].pop(module_name, None)
    
    @staticmethod
    def clear_all_module_states(context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        清理所有模块状态，但保留全局键
        
        Args:
            context: Telegram context
        """
        # 保存需要保留的全局数据
        preserved_data = {
            k: v for k, v in context.user_data.items() 
            if k in ModuleStateManager.PRESERVED_KEYS
        }
        
        # 清空所有用户数据
        context.user_data.clear()
        
        # 恢复保留的数据
        for key, value in preserved_data.items():
            context.user_data[key] = value
        
        # 重新初始化空的modules字典
        context.user_data['modules'] = {}
    
    @staticmethod
    def has_state(context: ContextTypes.DEFAULT_TYPE, module_name: str) -> bool:
        """
        检查是否存在模块状态
        
        Args:
            context: Telegram context
            module_name: 模块名称
            
        Returns:
            是否存在模块状态
        """
        return 'modules' in context.user_data and module_name in context.user_data['modules']
