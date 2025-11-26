"""
Premium 会员直充处理器 V2：支持给自己/他人开通
"""
import logging
from typing import Optional
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, User
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from src.common.conversation_wrapper import SafeConversationHandler
from src.common.navigation_manager import NavigationManager
from datetime import datetime, timedelta
import uuid

from ..models import OrderType, OrderStatus
from ..payments.order import OrderManager
from ..payments.suffix_manager import SuffixManager
from ..database import get_db, close_db, PremiumOrder
from ..config import settings
from ..common.decorators import error_handler, log_action
from ..common.settings_service import get_order_timeout_minutes
from .delivery import PremiumDeliveryService
from .recipient_parser import RecipientParser
from .user_verification import get_user_verification_service

logger = logging.getLogger(__name__)

# 对话状态
(
    SELECTING_TARGET,      # 选择给自己还是他人
    SELECTING_PACKAGE,     # 选择套餐
    ENTERING_USERNAME,     # 输入他人用户名
    AWAITING_USERNAME_ACTION,  # 等待用户名操作（重试或取消）
    VERIFYING_USERNAME,    # 验证用户名
    CONFIRMING_ORDER,      # 确认订单
    PROCESSING_PAYMENT     # 处理支付
) = range(7)


class PremiumHandlerV2:
    """Premium 购买对话处理器 V2"""
    
    # 套餐配置 {months: price_usdt}
    PACKAGES = {
        3: 16.0,
        6: 25.0,
        12: 35.0
    }
    
    def __init__(
        self,
        order_manager: OrderManager,
        suffix_manager: SuffixManager,
        delivery_service: PremiumDeliveryService,
        receive_address: str,
        bot_username: str = None
    ):
        """
        初始化处理器
        
        Args:
            order_manager: 订单管理器
            suffix_manager: 后缀管理器
            delivery_service: 交付服务
            receive_address: USDT 收款地址
            bot_username: Bot用户名
        """
        self.order_manager = order_manager
        self.suffix_manager = suffix_manager
        self.delivery_service = delivery_service
        self.receive_address = receive_address
        self.verification_service = get_user_verification_service(bot_username)
    
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
                    CallbackQueryHandler(self.retry_username_action, pattern=r'^retry_username_action$')
                ],
                VERIFYING_USERNAME: [
                    CallbackQueryHandler(self.confirm_username, pattern=r'^confirm_user$'),
                    CallbackQueryHandler(self.retry_username, pattern=r'^retry_user$')
                ],
                CONFIRMING_ORDER: [
                    CallbackQueryHandler(self.confirm_payment, pattern=r'^confirm_payment$'),
                    CallbackQueryHandler(self.cancel_order, pattern=r'^cancel_order$')
                ],
            },
            fallbacks=[
                # 只保留业务相关的fallback，导航由SafeConversationHandler处理
                MessageHandler(filters.Regex(r"^🔍 地址查询|👤 个人中心|⚡ 能量兑换|🔄 TRX 兑换|👨‍💼 联系客服|💵 实时U价|🎁 免费克隆$"), self.cancel_silent),
            ],
            allow_reentry=True,
            name="PremiumV2"
        )
    
    @error_handler
    @log_action("Premium_V2_开始")
    async def start_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始 Premium 购买流程"""
        # 自动绑定用户信息
        user = update.effective_user
        await self.verification_service.auto_bind_on_interaction(user)
        
        keyboard = [
            [
                InlineKeyboardButton("💎 给自己开通", callback_data="premium_self"),
                InlineKeyboardButton("🎁 给他人开通", callback_data="premium_other")
            ],
            [
                NavigationManager.create_back_button("❌ 取消")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "🎁 *Premium 会员开通*\n\n"
            "请选择开通方式：\n"
            "• 给自己开通 - 为您的账号开通Premium\n"
            "• 给他人开通 - 为指定用户开通Premium\n\n"
            "💰 套餐价格：\n"
            f"• 3个月 - ${self.PACKAGES[3]} USDT\n"
            f"• 6个月 - ${self.PACKAGES[6]} USDT\n"
            f"• 12个月 - ${self.PACKAGES[12]} USDT"
        )
        
        if update.message:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        return SELECTING_TARGET
    
    @log_action("Premium_V2_选择给自己")
    async def select_self(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """选择给自己开通"""
        query = update.callback_query
        await query.answer()
        
        try:
            user = update.effective_user
            context.user_data['recipient_type'] = 'self'
            context.user_data['recipient_id'] = user.id
            context.user_data['recipient_username'] = user.username or f"用户{user.id}"
            context.user_data['recipient_nickname'] = user.first_name
            
            logger.debug(f"Premium self purchase: user_id={user.id}, username={user.username}")
        
            # 显示用户信息和套餐选择
            keyboard = [
                [
                    InlineKeyboardButton(f"3个月 - ${self.PACKAGES[3]}", callback_data="premium_3"),
                    InlineKeyboardButton(f"6个月 - ${self.PACKAGES[6]}", callback_data="premium_6")
                ],
                [
                    InlineKeyboardButton(f"12个月 - ${self.PACKAGES[12]}", callback_data="premium_12")
                ],
                [
                    NavigationManager.create_back_button("❌ 取消")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = (
                f"✅ *为自己开通 Premium*\n\n"
                f"👤 开通账号：\n"
                f"• 用户名：@{user.username if user.username else '未设置'}\n"
                f"• 昵称：{user.first_name}\n\n"
                f"📦 请选择套餐时长："
            )
            
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return SELECTING_PACKAGE
            
        except Exception as e:
            logger.error(f"Error in select_self: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ 处理请求时出现错误，请稍后重试或联系客服。\n\n"
                f"错误详情：{str(e)}"
            )
            return ConversationHandler.END
    
    @log_action("Premium_V2_选择给他人")
    async def select_other(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """选择给他人开通"""
        query = update.callback_query
        await query.answer()
        
        try:
            context.user_data['recipient_type'] = 'other'
            logger.debug(f"Premium gift purchase initiated by user {update.effective_user.id}")
            
            await query.edit_message_text(
                "🎁 *为他人开通 Premium*\n\n"
                "请输入对方的 Telegram 用户名：\n"
                "• 支持格式：@username 或 username\n"
                "• 用户名需为 5-32 个字符\n"
                "• 仅支持字母、数字和下划线\n\n"
                "示例：@alice 或 alice",
                parse_mode='Markdown'
            )
            
            return ENTERING_USERNAME
            
        except Exception as e:
            logger.error(f"Error in select_other: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ 处理请求时出现错误，请稍后重试或联系客服。\n\n"
                f"错误详情：{str(e)}"
            )
            return ConversationHandler.END
    
    @error_handler
    @log_action("Premium_V2_输入用户名")
    async def username_entered(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理输入的用户名"""
        text = update.message.text.strip()
        
        # 解析用户名
        if text.startswith('@'):
            username = text[1:]
        else:
            username = text
        
        # 验证格式
        if not RecipientParser.validate_username(username):
            await update.message.reply_text(
                "❌ 用户名格式无效！\n\n"
                "用户名需要：\n"
                "• 5-32个字符\n"
                "• 仅包含字母、数字、下划线\n\n"
                "请重新输入："
            )
            return ENTERING_USERNAME
        
        # 验证用户是否存在
        result = await self.verification_service.verify_user_exists(username)
        
        context.user_data['recipient_username'] = username
        
        if result['exists'] and result['is_verified']:
            # 用户已验证
            context.user_data['recipient_id'] = result['user_id']
            context.user_data['recipient_nickname'] = result['nickname']
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ 确认", callback_data="confirm_user"),
                    InlineKeyboardButton("🔄 重新输入", callback_data="retry_user")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ *找到用户*\n\n"
                f"用户名：@{username}\n"
                f"昵称：{result['nickname']}\n\n"
                f"确认为此用户开通 Premium？",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return VERIFYING_USERNAME
        else:
            # 用户不存在或未验证
            keyboard = [
                [
                    InlineKeyboardButton("🔄 重新输入", callback_data="retry_username_action"),
                    NavigationManager.create_back_button("❌ 取消")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            msg = f"⚠️ *用户 @{username} "
            if not result['exists']:
                msg += "未找到*\n\n"
                msg += "可能原因：\n"
                msg += "• 用户名输入错误\n"
                msg += "• 用户未与本Bot交互过\n\n"
                msg += "请让对方先点击以下链接与Bot交互：\n"
                msg += f"{result['binding_url']}"
            else:
                msg += "未验证*\n\n"
                msg += "请让对方先与Bot交互进行验证"
            
            await update.message.reply_text(
                msg,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            # 返回等待动作状态，而不是文本输入状态
            return AWAITING_USERNAME_ACTION
    
    @error_handler
    async def confirm_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """确认用户名"""
        query = update.callback_query
        await query.answer()
        
        # 显示套餐选择
        keyboard = [
            [
                InlineKeyboardButton(f"3个月 - ${self.PACKAGES[3]}", callback_data="premium_3"),
                InlineKeyboardButton(f"6个月 - ${self.PACKAGES[6]}", callback_data="premium_6")
            ],
            [
                InlineKeyboardButton(f"12个月 - ${self.PACKAGES[12]}", callback_data="premium_12")
            ],
            [
                NavigationManager.create_back_button("❌ 取消")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        username = context.user_data.get('recipient_username')
        nickname = context.user_data.get('recipient_nickname', '未知')
        
        text = (
            f"🎁 *为他人开通 Premium*\n\n"
            f"👤 接收用户：\n"
            f"• 用户名：@{username}\n"
            f"• 昵称：{nickname}\n\n"
            f"📦 请选择套餐时长："
        )
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return SELECTING_PACKAGE
    
    @error_handler
    async def retry_username_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理重新输入用户名的动作"""
        query = update.callback_query
        await query.answer()
        
        # 发送新消息引导用户输入，而不是编辑
        await update.effective_message.reply_text(
            "🎁 *为他人开通 Premium*\n\n"
            "请重新输入对方的 Telegram 用户名：\n"
            "• 支持格式：@username 或 username\n"
            "• 用户名需为 5-32 个字符\n\n"
            "示例：@alice 或 alice",
            parse_mode='Markdown'
        )
        
        return ENTERING_USERNAME
    
    @error_handler
    async def retry_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """重新输入用户名（从验证页面）"""
        query = update.callback_query
        await query.answer()
        
        # 发送新消息而不是编辑
        await update.effective_message.reply_text(
            "🎁 *为他人开通 Premium*\n\n"
            "请重新输入对方的 Telegram 用户名：",
            parse_mode='Markdown'
        )
        
        return ENTERING_USERNAME
    
    @error_handler
    @log_action("Premium_V2_选择套餐")
    async def package_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """用户选择套餐"""
        query = update.callback_query
        await query.answer()
        
        # 解析月数
        months = int(query.data.split('_')[1])
        context.user_data['premium_months'] = months
        context.user_data['base_amount'] = self.PACKAGES[months]
        
        # 创建订单
        try:
            db = get_db()
            
            # 创建 Premium 订单
            order_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(minutes=get_order_timeout_minutes())
            
            premium_order = PremiumOrder(
                order_id=order_id,
                buyer_id=update.effective_user.id,
                recipient_id=context.user_data.get('recipient_id'),
                recipient_username=context.user_data.get('recipient_username'),
                recipient_type=context.user_data['recipient_type'],
                premium_months=months,
                amount_usdt=self.PACKAGES[months],
                status='PENDING',
                expires_at=expires_at
            )
            
            db.add(premium_order)
            db.commit()
            
            context.user_data['order_id'] = order_id
            
            # 同时创建支付订单（用于接收支付）
            payment_order = await self.order_manager.create_order(
                user_id=update.effective_user.id,
                base_amount=self.PACKAGES[months],
                order_type=OrderType.PREMIUM,
                premium_months=months,
                recipients=[context.user_data.get('recipient_username')]
            )
            
            if payment_order:
                context.user_data['payment_order_id'] = payment_order.order_id
                context.user_data['total_amount'] = payment_order.total_amount
                context.user_data['unique_suffix'] = payment_order.unique_suffix
            else:
                raise RuntimeError("Failed to create payment order")
            
        except Exception as e:
            logger.error(f"Failed to create premium order: {e}")
            await query.edit_message_text(
                "❌ 创建订单失败，请稍后重试或联系客服。"
            )
            return ConversationHandler.END
        finally:
            close_db(db)
        
        # 显示订单确认
        keyboard = [
            [
                InlineKeyboardButton("✅ 确认支付", callback_data="confirm_payment"),
                InlineKeyboardButton("❌ 取消订单", callback_data="cancel_order")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        recipient_info = ""
        if context.user_data['recipient_type'] == 'self':
            recipient_info = "👤 接收账号：您自己"
        else:
            username = context.user_data.get('recipient_username')
            nickname = context.user_data.get('recipient_nickname', '未知')
            recipient_info = f"👤 接收账号：@{username} ({nickname})"
        
        remaining_minutes = int((expires_at - datetime.now()).total_seconds() / 60)
        
        text = (
            f"📦 *订单确认*\n\n"
            f"套餐：{months} 个月 Premium\n"
            f"{recipient_info}\n\n"
            f"💰 应付金额：`{context.user_data['total_amount']:.3f}` USDT (TRC20)\n"
            f"📍 收款地址：`{self.receive_address}`\n\n"
            f"⏰ 订单有效期：{remaining_minutes} 分钟\n"
            f"📝 订单号：`{order_id}`"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return CONFIRMING_ORDER
    
    @error_handler
    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """用户确认支付"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            f"✅ *订单已创建*\n\n"
            f"💰 应付金额：`{context.user_data['total_amount']:.3f}` USDT\n"
            f"📍 收款地址：`{self.receive_address}`\n\n"
            f"⚠️ 请精确转账 `{context.user_data['total_amount']:.3f}` USDT（包含小数部分）\n"
            f"⏰ 支付后 2-5 分钟内自动到账\n\n"
            f"🔖 订单号：`{context.user_data['order_id']}`",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    @error_handler
    async def cancel_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消订单"""
        query = update.callback_query
        await query.answer()
        
        # 取消支付订单
        if 'payment_order_id' in context.user_data:
            await self.order_manager.cancel_order(context.user_data['payment_order_id'])
        
        # 更新Premium订单状态
        if 'order_id' in context.user_data:
            db = get_db()
            try:
                order = db.query(PremiumOrder).filter(
                    PremiumOrder.order_id == context.user_data['order_id']
                ).first()
                if order:
                    order.status = 'CANCELLED'
                    db.commit()
            finally:
                close_db(db)
        
        await query.edit_message_text("❌ 订单已取消")
        
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消对话 - 使用统一清理机制"""
        # 先发送取消确认
        if update.callback_query:
            await update.callback_query.answer("已取消")
        
        # 使用统一的清理和导航方法
        return await NavigationManager.cleanup_and_show_main_menu(update, context)
    
    async def cancel_silent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """静默取消对话"""
        # 清除对话数据
        for key in ['recipient_type', 'recipient_id', 'recipient_username', 
                    'recipient_nickname', 'premium_months', 'base_amount',
                    'order_id', 'payment_order_id', 'total_amount', 'unique_suffix']:
            context.user_data.pop(key, None)
        return ConversationHandler.END
