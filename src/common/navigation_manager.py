"""
统一导航管理器
处理所有跨模块导航，确保按钮交互的一致性
"""
import logging
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

logger = logging.getLogger(__name__)

class NavigationManager:
    """统一导航管理器 - 处理所有跨模块导航"""
    
    # 导航目标映射
    NAVIGATION_TARGETS = {
        'back_to_main': 'main_menu',
        'nav_back_to_main': 'main_menu',
        'menu_back_to_main': 'main_menu',
        'addrq_back_to_main': 'main_menu',
        'menu_profile': 'profile',
        'menu_premium': 'premium',
        'menu_address_query': 'address_query',
        'menu_energy': 'energy',
        'menu_trx_exchange': 'trx_exchange',
        'menu_support': 'support',
        'menu_clone': 'clone',
        'menu_help': 'help',
        'menu_admin': 'admin',
        'admin_back': 'admin_menu',  # 管理员面板返回
        'orders_back': 'orders_menu',  # 订单管理返回
    }
    
    # 需要保留的用户数据键
    PRESERVED_KEYS = [
        'user_id', 'username', 'first_name', 'is_admin',
        'language', 'last_command', 'current_module',
        'main_menu_keyboard_shown'  # 保留键盘显示状态，避免重复提示
    ]
    
    @classmethod
    async def handle_navigation(
        cls, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE,
        target: Optional[str] = None
    ) -> int:
        """
        处理导航请求
        
        Args:
            update: Telegram更新
            context: 上下文
            target: 导航目标，如果为None则从callback_data获取
            
        Returns:
            ConversationHandler.END 结束当前对话
        """
        query = update.callback_query
        if query:
            await query.answer()
            target = target or query.data
        
        # 记录导航事件
        user = update.effective_user
        logger.info(f"用户 {user.id} ({user.username}) 导航到: {target}")
        
        # 清理会话状态（保留必要数据）
        cls._cleanup_conversation_data(context)
        
        # 也清理chat_data - 结束对话时应该清理所有临时数据
        context.chat_data.clear()
        
        # 路由到目标
        if target in ['back_to_main', 'nav_back_to_main', 'menu_back_to_main', 'addrq_back_to_main']:
            await cls._show_main_menu(update, context)
        elif target == 'admin_back':
            await cls._show_admin_menu(update, context)
        elif target == 'orders_back':
            await cls._show_orders_menu(update, context)
        elif target.startswith('menu_'):
            # 其他菜单项由主菜单处理
            await cls._show_main_menu(update, context)
        else:
            logger.warning(f"Unknown navigation target: {target}")
            await cls._show_main_menu(update, context)
        
        return ConversationHandler.END
    
    @classmethod
    def _cleanup_conversation_data(cls, context: ContextTypes.DEFAULT_TYPE):
        """
        清理会话数据，保留必要信息
        
        Args:
            context: 上下文
        """
        # 保留必要的用户数据
        preserved_data = {
            k: v for k, v in context.user_data.items() 
            if k in cls.PRESERVED_KEYS
        }
        
        # 清理并恢夏
        context.user_data.clear()
        context.user_data.update(preserved_data)
        
        logger.debug(f"用户数据已清理，保留键: {list(preserved_data.keys())}")
    
    @classmethod
    async def cleanup_and_show_main_menu(
        cls, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """
        清理数据并显示主菜单（供各模块cancel方法调用）
        
        这是统一的取消处理方法，确保：
        1. 保留重要状态（如main_menu_keyboard_shown）
        2. 清理临时数据（如订单ID、输入状态）
        3. 显示主菜单
        
        Args:
            update: Telegram更新
            context: 上下文
            
        Returns:
            ConversationHandler.END
        """
        user = update.effective_user
        logger.info(f"用户 {user.id} 取消当前操作，返回主菜单")
        
        # 清理数据
        cls._cleanup_conversation_data(context)
        
        # 显示主菜单
        await cls._show_main_menu(update, context)
        
        return ConversationHandler.END
    
    @staticmethod
    async def _show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示主菜单"""
        from ..menu.main_menu import MainMenuHandler
        await MainMenuHandler.show_main_menu(update, context)
    
    @staticmethod
    async def _show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示管理员菜单"""
        from ..bot_admin.menus import AdminMenus
        query = update.callback_query
        if query:
            await AdminMenus.show_main_menu(query)
    
    @staticmethod
    async def _show_orders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示订单管理菜单"""
        # TODO: 实现订单管理菜单显示
        # 暂时返回主菜单
        await NavigationManager._show_main_menu(update, context)
    
    @classmethod
    def create_back_button(
        cls, 
        text: str = "🔙 返回主菜单",
        callback_data: str = "nav_back_to_main"
    ) -> InlineKeyboardButton:
        """
        创建标准返回按钮
        
        Args:
            text: 按钮文本
            callback_data: 回调数据
            
        Returns:
            InlineKeyboardButton
        """
        return InlineKeyboardButton(text, callback_data=callback_data)
    
    @classmethod
    def create_navigation_row(
        cls,
        include_back: bool = True,
        include_cancel: bool = False,
        back_text: str = "🔙 返回",
        cancel_text: str = "❌ 取消"
    ) -> list:
        """
        创建导航按钮行
        
        Args:
            include_back: 是否包含返回按钮
            include_cancel: 是否包含取消按钮
            back_text: 返回按钮文本
            cancel_text: 取消按钮文本
            
        Returns:
            按钮列表
        """
        buttons = []
        if include_back:
            buttons.append(cls.create_back_button(back_text))
        if include_cancel:
            buttons.append(InlineKeyboardButton(cancel_text, callback_data="cancel"))
        return buttons
    
    @classmethod
    def standardize_keyboard(
        cls,
        keyboard: list,
        add_back_button: bool = True
    ) -> list:
        """
        标准化键盘布局，确保有返回按钮
        
        Args:
            keyboard: 原始键盘布局
            add_back_button: 是否添加返回按钮
            
        Returns:
            标准化的键盘布局
        """
        if add_back_button:
            # 检查是否已有返回按钮
            has_back = False
            for row in keyboard:
                for button in row:
                    if button.callback_data in ['back_to_main', 'nav_back_to_main']:
                        has_back = True
                        break
                if has_back:
                    break
            
            # 如果没有返回按钮，添加一个
            if not has_back:
                keyboard.append([cls.create_back_button()])
        
        return keyboard
    
    @classmethod
    async def handle_fallback_callback(
        cls,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """
        兜底回调处理器 - 处理未被其他 handler 捕获的回调
        
        放在 group=100，作为最后的安全网。
        
        Args:
            update: Telegram更新
            context: 上下文
            
        Returns:
            ConversationHandler.END
        """
        query = update.callback_query
        if query:
            await query.answer()
            
            user = update.effective_user
            callback_data = query.data
            logger.warning(
                f"兜底处理器捕获未处理的回调: user={user.id}, data={callback_data}"
            )
            
            # 清理状态并返回主菜单
            cls._cleanup_conversation_data(context)
            context.chat_data.clear()
            await cls._show_main_menu(update, context)
        
        return ConversationHandler.END
