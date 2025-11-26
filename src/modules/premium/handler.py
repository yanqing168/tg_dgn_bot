"""
Premium模块主处理器 - 标准化版本
修复了Markdown解析错误，统一使用HTML格式
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from telegram import Update
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    BaseHandler
)

from src.core.base import BaseModule
from src.core.formatter import MessageFormatter
from src.core.state_manager import ModuleStateManager
from src.common.navigation_manager import NavigationManager
from src.common.conversation_wrapper import SafeConversationHandler
from src.common.settings_service import get_order_timeout_minutes
from src.models import OrderType

from .states import *
from .messages import PremiumMessages
from .keyboards import PremiumKeyboards


logger = logging.getLogger(__name__)


class PremiumModule(BaseModule):
    """标准化的Premium模块"""
    
    # 套餐配置 {months: price_usdt}
    PACKAGES = {
        3: 16.0,
        6: 25.0,
        12: 35.0
    }
    
    def __init__(
        self,
        order_manager,
        suffix_manager,
        delivery_service,
        receive_address: str,
        bot_username: str = None
    ):
        """
        初始化Premium模块
        
        Args:
            order_manager: 订单管理器
            suffix_manager: 后缀管理器
            delivery_service: 交付服务
            receive_address: USDT收款地址
            bot_username: Bot用户名
        """
        self.order_manager = order_manager
        self.suffix_manager = suffix_manager
        self.delivery_service = delivery_service
        self.receive_address = receive_address
        self.bot_username = bot_username
        
        # 核心组件
        self.formatter = MessageFormatter()
        self.state_manager = ModuleStateManager()
        
        # 验证服务（保持兼容）
        from src.premium.user_verification import get_user_verification_service
        self.verification_service = get_user_verification_service(bot_username)
        
        # 收件人解析器（保持兼容）
    
    @property
    def module_name(self) -> str:
        """模块名称"""
        return "premium"
    
    def get_handlers(self) -> List[BaseHandler]:
        """获取模块处理器"""
        return [self.get_conversation_handler()]
    
    def get_conversation_handler(self) -> ConversationHandler:
        """获取对话处理器"""
        return SafeConversationHandler.create(
            entry_points=[
                CommandHandler('premium', self.start_premium),
                MessageHandler(filters.Regex(r"^💎 Premium会员$"), self.start_premium),
                CallbackQueryHandler(self.start_premium, pattern=r"^menu_premium$"),
            ],
            states={
                SELECTING_TARGET: [
                    CallbackQueryHandler(self.select_self, pattern=r'^premium_self$'),
                    CallbackQueryHandler(self.select_other, pattern=r'^premium_other$')
                ],
                SELECTING_PACKAGE: [
                    CallbackQueryHandler(self.package_selected, pattern=r'^premium_\d+$')
                ],
                ENTERING_USERNAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.username_entered)
                ],
                AWAITING_USERNAME_ACTION: [
                    CallbackQueryHandler(self.retry_username_action, pattern=r'^premium_retry_username$')
                ],
                VERIFYING_USERNAME: [
                    CallbackQueryHandler(self.confirm_username, pattern=r'^premium_confirm_user$'),
                    CallbackQueryHandler(self.retry_username, pattern=r'^premium_retry_user$')
                ],
                CONFIRMING_ORDER: [
                    CallbackQueryHandler(self.confirm_payment, pattern=r'^premium_confirm_payment$'),
                    CallbackQueryHandler(self.cancel_order, pattern=r'^premium_cancel_order$')
                ],
            },
            fallbacks=[
                MessageHandler(
                    filters.Regex(r"^🔍 地址查询|👤 个人中心|⚡ 能量兑换|🔄 TRX 兑换|👨‍💼 联系客服|💵 实时U价|🎁 免费克隆$"), 
                    self.cancel_silent
                ),
            ],
            allow_reentry=True,
            name="premium_standard"
        )
    
    async def start_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始Premium购买流程"""
        logger.info(f"Premium start - user: {update.effective_user.id}")
        
        # 自动绑定用户信息
        user = update.effective_user
        await self.verification_service.auto_bind_on_interaction(user)
        
        # 初始化模块状态
        self.state_manager.init_state(context, self.module_name)
        
        # 格式化消息
        text = self.formatter.format_html(
            PremiumMessages.START,
            price_3=self.PACKAGES[3],
            price_6=self.PACKAGES[6],
            price_12=self.PACKAGES[12]
        )
        
        keyboard = PremiumKeyboards.start_keyboard()
        
        # 发送消息
        if update.message:
            await update.message.reply_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        
        return SELECTING_TARGET
    
    async def select_self(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """选择给自己开通"""
        query = update.callback_query
        await query.answer()
        
        try:
            user = update.effective_user
            
            # 保存状态
            state = self.state_manager.get_state(context, self.module_name)
            state['recipient_type'] = 'self'
            state['recipient_id'] = user.id
            state['recipient_username'] = user.username or f"用户{user.id}"
            state['recipient_nickname'] = user.first_name
            
            logger.debug(f"Premium self purchase: user_id={user.id}, username={user.username}")
            
            # 格式化消息 - 注意safe_username和safe_nickname已经包含了转义
            username_display = self.formatter.safe_username(user.username)
            nickname_display = self.formatter.safe_nickname(user.first_name)
            
            # 直接使用模板，因为username和nickname已经是安全的HTML
            text = PremiumMessages.SELECT_SELF.format(
                username=username_display,
                nickname=nickname_display
            )
            
            keyboard = PremiumKeyboards.package_keyboard(self.PACKAGES)
            
            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            return SELECTING_PACKAGE
            
        except Exception as e:
            logger.error(f"Error in select_self: {e}", exc_info=True)
            error_text = PremiumMessages.ERROR_GENERAL.format(
                error=self.formatter.escape_html(str(e))
            )
            await query.edit_message_text(
                error_text,
                parse_mode='HTML',
                reply_markup=PremiumKeyboards.back_to_main_keyboard()
            )
            return ConversationHandler.END
    
    async def select_other(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """选择给他人开通"""
        query = update.callback_query
        await query.answer()
        
        try:
            # 保存状态
            state = self.state_manager.get_state(context, self.module_name)
            state['recipient_type'] = 'other'
            
            logger.debug(f"Premium gift purchase initiated by user {update.effective_user.id}")
            
            await query.edit_message_text(
                PremiumMessages.SELECT_OTHER,
                parse_mode='HTML'
            )
            
            return ENTERING_USERNAME
            
        except Exception as e:
            logger.error(f"Error in select_other: {e}", exc_info=True)
            error_text = PremiumMessages.ERROR_GENERAL.format(
                error=self.formatter.escape_html(str(e))
            )
            await query.edit_message_text(
                error_text,
                parse_mode='HTML',
                reply_markup=PremiumKeyboards.back_to_main_keyboard()
            )
            return ConversationHandler.END
    
    async def username_entered(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理输入的用户名"""
        text = update.message.text.strip()
        
        # 解析用户名
        if text.startswith('@'):
            username = text[1:]
        else:
            username = text
        
        # 验证格式
        from src.premium.recipient_parser import RecipientParser
        if not RecipientParser.validate_username(username):
            await update.message.reply_text(
                PremiumMessages.INVALID_USERNAME,
                parse_mode='HTML'
            )
            return ENTERING_USERNAME
        
        # 验证用户是否存在
        result = await self.verification_service.verify_user_exists(username)
        
        # 保存状态
        state = self.state_manager.get_state(context, self.module_name)
        state['recipient_username'] = username
        
        if result['exists'] and result['is_verified']:
            # 用户已验证
            state['recipient_id'] = result['user_id']
            state['recipient_nickname'] = result['nickname']
            
            # 对用户名和昵称进行转义
            escaped_username = self.formatter.escape_html(username)
            escaped_nickname = self.formatter.escape_html(result['nickname'])
            
            text = PremiumMessages.USER_FOUND.format(
                username=escaped_username,
                nickname=escaped_nickname
            )
            
            await update.message.reply_text(
                text,
                reply_markup=PremiumKeyboards.confirm_user_keyboard(),
                parse_mode='HTML'
            )
            
            return VERIFYING_USERNAME
        else:
            # 用户不存在或未验证
            escaped_username = self.formatter.escape_html(username)
            if not result['exists']:
                text = PremiumMessages.USER_NOT_FOUND.format(
                    username=escaped_username,
                    binding_url=result.get('binding_url', '')
                )
            else:
                text = PremiumMessages.USER_NOT_VERIFIED.format(
                    username=escaped_username
                )
            
            await update.message.reply_text(
                text,
                reply_markup=PremiumKeyboards.retry_or_cancel_keyboard(),
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            return AWAITING_USERNAME_ACTION
    
    async def confirm_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """确认用户名"""
        query = update.callback_query
        await query.answer()
        
        state = self.state_manager.get_state(context, self.module_name)
        username = state.get('recipient_username')
        nickname = state.get('recipient_nickname', '未知')
        
        escaped_username = self.formatter.escape_html(username)
        escaped_nickname = self.formatter.escape_html(nickname)
        
        text = PremiumMessages.SELECT_OTHER_CONFIRM.format(
            username=escaped_username,
            nickname=escaped_nickname
        )
        
        keyboard = PremiumKeyboards.package_keyboard(self.PACKAGES)
        
        await query.edit_message_text(
            text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        
        return SELECTING_PACKAGE
    
    async def retry_username_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理重新输入用户名的动作"""
        query = update.callback_query
        await query.answer()
        
        await update.effective_message.reply_text(
            PremiumMessages.SELECT_OTHER,
            parse_mode='HTML'
        )
        
        return ENTERING_USERNAME
    
    async def retry_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """重新输入用户名（从验证页面）"""
        query = update.callback_query
        await query.answer()
        
        await update.effective_message.reply_text(
            PremiumMessages.SELECT_OTHER,
            parse_mode='HTML'
        )
        
        return ENTERING_USERNAME
    
    async def package_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """用户选择套餐"""
        query = update.callback_query
        await query.answer()
        
        # 解析月数
        months = int(query.data.split('_')[1])
        
        # 保存状态
        state = self.state_manager.get_state(context, self.module_name)
        state['premium_months'] = months
        state['base_amount'] = self.PACKAGES[months]
        
        # 创建订单
        try:
            # 获取数据库连接
            from src.database import get_db, close_db
            from src.database import PremiumOrder
            db = get_db()
            
            # 创建Premium订单
            order_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(minutes=get_order_timeout_minutes())
            
            premium_order = PremiumOrder(
                order_id=order_id,
                buyer_id=update.effective_user.id,
                recipient_id=state.get('recipient_id'),
                recipient_username=state.get('recipient_username'),
                recipient_type=state['recipient_type'],
                premium_months=months,
                amount_usdt=self.PACKAGES[months],
                status='PENDING',
                expires_at=expires_at
            )
            
            db.add(premium_order)
            db.commit()
            
            state['order_id'] = order_id
            
            # 同时创建支付订单
            payment_order = await self.order_manager.create_order(
                user_id=update.effective_user.id,
                base_amount=self.PACKAGES[months],
                order_type=OrderType.PREMIUM,
                premium_months=months,
                recipients=[state.get('recipient_username')]
            )
            
            if payment_order:
                state['payment_order_id'] = payment_order.order_id
                state['total_amount'] = payment_order.total_amount
                state['unique_suffix'] = payment_order.unique_suffix
            else:
                raise RuntimeError("Failed to create payment order")
            
        except Exception as e:
            logger.error(f"Failed to create premium order: {e}")
            await query.edit_message_text(
                PremiumMessages.ERROR_CREATE_ORDER,
                parse_mode='HTML',
                reply_markup=PremiumKeyboards.back_to_main_keyboard()
            )
            return ConversationHandler.END
        finally:
            close_db(db)
        
        # 显示订单确认
        recipient_info = ""
        if state['recipient_type'] == 'self':
            recipient_info = "👤 接收账号：您自己"
        else:
            username = state.get('recipient_username')
            nickname = state.get('recipient_nickname', '未知')
            username_display = self.formatter.safe_username(username)
            nickname_display = self.formatter.safe_nickname(nickname)
            recipient_info = f"👤 接收账号：{username_display} ({nickname_display})"
        
        remaining_minutes = int((expires_at - datetime.now()).total_seconds() / 60)
        
        # 注意：recipient_info已经包含了安全的HTML，其他字段是数字或已知安全的字符串
        text = PremiumMessages.ORDER_CONFIRM.format(
            months=months,
            recipient_info=recipient_info,
            amount=state['total_amount'],
            address=self.receive_address,
            remaining=remaining_minutes,
            order_id=order_id
        )
        
        keyboard = PremiumKeyboards.confirm_order_keyboard()
        
        await query.edit_message_text(
            text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        
        return CONFIRMING_ORDER
    
    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """用户确认支付"""
        query = update.callback_query
        await query.answer()
        
        state = self.state_manager.get_state(context, self.module_name)
        
        text = PremiumMessages.ORDER_CREATED.format(
            amount=state['total_amount'],
            address=self.receive_address,
            order_id=state['order_id']
        )
        
        await query.edit_message_text(
            text,
            parse_mode='HTML'
        )
        
        # 清理模块状态
        self.state_manager.clear_state(context, self.module_name)
        
        return ConversationHandler.END
    
    async def cancel_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消订单"""
        query = update.callback_query
        await query.answer()
        
        state = self.state_manager.get_state(context, self.module_name)
        
        # 取消支付订单
        if 'payment_order_id' in state:
            await self.order_manager.cancel_order(state['payment_order_id'])
        
        # 更新Premium订单状态
        if 'order_id' in state:
            from src.database import get_db, close_db, PremiumOrder
            db = get_db()
            try:
                order = db.query(PremiumOrder).filter(
                    PremiumOrder.order_id == state['order_id']
                ).first()
                if order:
                    order.status = 'CANCELLED'
                    db.commit()
            finally:
                close_db(db)
        
        await query.edit_message_text(
            PremiumMessages.ORDER_CANCELLED,
            parse_mode='HTML'
        )
        
        # 清理模块状态
        self.state_manager.clear_state(context, self.module_name)
        
        return ConversationHandler.END
    
    async def cancel_silent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """静默取消对话"""
        # 清理模块状态
        self.state_manager.clear_state(context, self.module_name)
        return ConversationHandler.END
