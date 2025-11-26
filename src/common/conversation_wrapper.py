"""
ConversationHandler包装器
确保所有对话处理器的一致性和隔离性
"""
import logging
from typing import List, Dict, Any, Optional
from telegram.ext import (
    ConversationHandler, 
    CallbackQueryHandler, 
    CommandHandler,
    MessageHandler,
    filters
)
from .navigation_manager import NavigationManager

logger = logging.getLogger(__name__)

class SafeConversationHandler:
    """安全的对话处理器包装器"""
    
    # 全局导航模式列表
    NAVIGATION_PATTERNS = [
        r'^(back_to_main|nav_back_to_main|menu_back_to_main|addrq_back_to_main)$',  # 返回主菜单
        r'^admin_back$',  # 管理员面板返回
        r'^orders_back$',  # 订单管理返回
    ]
    
    # 菜单切换模式（需要结束当前对话）
    MENU_SWITCH_PATTERNS = [
        r'^menu_(profile|address_query|energy|trx_exchange|premium|support|clone|help|admin)$'
    ]
    
    # 全局命令（始终可用）
    GLOBAL_COMMANDS = ['start', 'help', 'cancel']
    
    @classmethod
    def create(
        cls,
        entry_points: List,
        states: Dict,
        fallbacks: List,
        allow_reentry: bool = True,
        name: Optional[str] = None,
        per_message: bool = False,
        per_chat: bool = True,
        per_user: bool = True,
        conversation_timeout: Optional[int] = None
    ) -> ConversationHandler:
        """
        创建安全的ConversationHandler
        
        Args:
            entry_points: 入口点列表
            states: 状态字典
            fallbacks: 回退处理器列表
            allow_reentry: 是否允许重入
            name: 处理器名称（用于日志）
            per_message: 是否为每条消息创建独立对话
            per_chat: 是否为每个聊天创建独立对话
            per_user: 是否为每个用户创建独立对话
            conversation_timeout: 对话超时时间（秒）
            
        Returns:
            配置好的ConversationHandler
        """
        name = name or "unnamed"
        logger.info(f"创建安全对话处理器: {name}")
        
        # 构建安全的fallbacks
        safe_fallbacks = cls._build_safe_fallbacks(fallbacks, name)
        
        # 创建ConversationHandler
        handler = ConversationHandler(
            entry_points=entry_points,
            states=states,
            fallbacks=safe_fallbacks,
            allow_reentry=allow_reentry,
            name=name,
            per_message=per_message,
            per_chat=per_chat,
            per_user=per_user,
            conversation_timeout=conversation_timeout
        )
        
        logger.info(f"✅ 安全对话处理器 '{name}' 创建成功")
        return handler
    
    @classmethod
    def _build_safe_fallbacks(cls, original_fallbacks: List, handler_name: str) -> List:
        """
        构建安全的fallback列表
        
        Args:
            original_fallbacks: 原始fallback列表
            handler_name: 处理器名称
            
        Returns:
            安全的fallback列表
        """
        safe_fallbacks = []
        
        # 1. 不在这里添加导航处理 - NavigationManager已在group=0全局注册
        # 由于NavigationManager在group=0（最高优先级）全局注册，
        # 所有导航回调都会被它拦截并处理
        # 如果在这里再添加，会导致重复处理
        logger.debug(f"SafeConversationHandler '{handler_name}': 导航由全局NavigationManager处理")
        
        # 2. 添加菜单切换处理 - 这些不会和全局导航冲突
        for pattern in cls.MENU_SWITCH_PATTERNS:
            safe_fallbacks.append(
                CallbackQueryHandler(
                    cls._handle_menu_switch,
                    pattern=pattern
                )
            )
        
        # 3. 添加全局命令处理
        safe_fallbacks.append(
            CommandHandler('cancel', cls._handle_cancel)
        )
        
        # 4. 过滤并添加原始fallbacks
        for fb in original_fallbacks:
            if cls._should_include_fallback(fb):
                safe_fallbacks.append(fb)
            else:
                logger.debug(f"过滤掉fallback: {fb}")
        
        # 5. 添加默认错误处理
        safe_fallbacks.append(
            MessageHandler(
                filters.ALL,
                lambda u, c: cls._handle_unexpected_input(u, c, handler_name)
            )
        )
        
        return safe_fallbacks
    
    @classmethod
    def _should_include_fallback(cls, fallback) -> bool:
        """
        判断是否应该包含某个fallback
        
        Args:
            fallback: 原始fallback处理器
            
        Returns:
            是否包含
        """
        # 跳过会干扰导航的处理器
        if isinstance(fallback, CallbackQueryHandler):
            pattern = getattr(fallback.pattern, 'pattern', None) if hasattr(fallback, 'pattern') else None
            if pattern:
                pattern_str = str(pattern)
                # 检查是否包含导航相关模式
                skip_patterns = [
                    'back_to_main', 'nav_back_to_main', 'menu_back_to_main', 'addrq_back_to_main',
                    'admin_back', 'orders_back'
                ]
                for skip in skip_patterns:
                    if skip in pattern_str:
                        return False
        
        return True
    
    @staticmethod
    async def _handle_cancel(update, context) -> int:
        """处理取消命令"""
        user = update.effective_user
        logger.info(f"用户 {user.id} 取消当前对话")
        
        # 清理数据并返回主菜单
        NavigationManager._cleanup_conversation_data(context)
        await NavigationManager._show_main_menu(update, context)
        
        return ConversationHandler.END
    
    @staticmethod
    async def _handle_menu_switch(update, context) -> int:
        """处理菜单切换"""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        target = query.data
        logger.info(f"用户 {user.id} 切换到菜单: {target}")
        
        # 结束当前对话，让主处理器接管
        NavigationManager._cleanup_conversation_data(context)
        return ConversationHandler.END
    
    @staticmethod
    async def _handle_unexpected_input(update, context, handler_name: str):
        """处理意外输入"""
        user = update.effective_user
        logger.warning(f"用户 {user.id} 在 {handler_name} 中发送了意外输入")
        
        # 不做任何响应，保持在当前状态
        return None
    
    @classmethod
    def create_simple(
        cls,
        command: str,
        handler_func,
        states: Optional[Dict] = None,
        name: Optional[str] = None
    ) -> ConversationHandler:
        """
        创建简单的对话处理器（单命令入口）
        
        Args:
            command: 命令名称
            handler_func: 处理函数
            states: 状态字典（可选）
            name: 处理器名称
            
        Returns:
            配置好的ConversationHandler
        """
        entry_points = [CommandHandler(command, handler_func)]
        states = states or {}
        fallbacks = []
        
        return cls.create(
            entry_points=entry_points,
            states=states,
            fallbacks=fallbacks,
            name=name or f"simple_{command}"
        )
