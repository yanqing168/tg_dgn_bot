"""
Premium 会员直充处理器：Telegram Bot 对话流程
"""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CommandHandler, 
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from ..models import OrderType
from ..payments.order import OrderManager
from ..payments.suffix_manager import SuffixManager
from ..models import Order, OrderStatus
from ..config import settings
from src.common.decorators import error_handler, log_action
from src.common.settings_service import get_order_timeout_minutes
from .delivery import PremiumDeliveryService
from .recipient_parser import RecipientParser

logger = logging.getLogger(__name__)

# 对话状态
SELECTING_PACKAGE, ENTERING_RECIPIENTS, CONFIRMING_PAYMENT = range(3)


class PremiumHandler:
    """Premium 购买对话处理器"""
    
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
        receive_address: str
    ):
        """
        初始化处理器
        
        Args:
            order_manager: 订单管理器
            suffix_manager: 后缀管理器
            delivery_service: 交付服务
            receive_address: USDT 收款地址
        """
        self.order_manager = order_manager
        self.suffix_manager = suffix_manager
        self.delivery_service = delivery_service
        self.receive_address = receive_address
    
    def get_conversation_handler(self) -> ConversationHandler:
        """
        获取对话处理器
        
        Returns:
            ConversationHandler 实例
        """
        return ConversationHandler(
            entry_points=[
                CommandHandler('premium', self.start_premium),
                MessageHandler(filters.Regex(r"^💎 Premium会员$"), self.start_premium),
                CallbackQueryHandler(self.start_premium, pattern=r"^menu_premium$"),
            ],
            states={
                SELECTING_PACKAGE: [
                    CallbackQueryHandler(self.package_selected, pattern=r'^premium_\d+$')
                ],
                ENTERING_RECIPIENTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.recipients_entered)
                ],
                CONFIRMING_PAYMENT: [
                    CallbackQueryHandler(self.confirm_payment, pattern=r'^confirm_payment$'),
                    CallbackQueryHandler(self.cancel_order, pattern=r'^cancel_order$')
                ],
            },
            fallbacks=[
                CommandHandler('cancel', self.cancel),
                # 当用户点击其他功能按钮时，自动结束当前对话
                CallbackQueryHandler(self.cancel_silent, pattern="^(menu_profile|menu_address_query|menu_energy|menu_clone|menu_support|menu_trx_exchange|back_to_main)$"),
                # 处理Reply键盘按钮
                MessageHandler(filters.Regex(r"^(🔍 地址查询|👤 个人中心|⚡ 能量兑换|🔄 TRX 兑换|👨‍💼 联系客服|💵 实时U价|🎁 免费克隆)$"), self.cancel_silent),
            ],
            allow_reentry=True
        )
    
    @error_handler
    @log_action("Premium_开始")
    async def start_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        开始 Premium 购买流程
        
        Args:
            update: Telegram 更新
            context: 上下文
            
        Returns:
            下一个对话状态
        """
        keyboard = [
            [
                InlineKeyboardButton(f"3个月 - ${self.PACKAGES[3]}", callback_data="premium_3"),
                InlineKeyboardButton(f"6个月 - ${self.PACKAGES[6]}", callback_data="premium_6")
            ],
            [
                InlineKeyboardButton(f"12个月 - ${self.PACKAGES[12]}", callback_data="premium_12")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        def format_price(value: float) -> str:
            return str(int(value)) if value.is_integer() else f"{value:.2f}".rstrip('0').rstrip('.')

        pricing_table = (
            "```\n"
            "| 时长 | 3个月 | 6个月 | 12个月 |\n"
            "|------|------|------|--------|\n"
            f"| 价格 | {format_price(self.PACKAGES[3])} U | {format_price(self.PACKAGES[6])} U | {format_price(self.PACKAGES[12])} U |\n"
            "```"
        )

        text = (
            "🎁 *Premium 会员直充*\n\n"
            "选择套餐后，请提供收件人用户名（支持 @username 或 t.me/username 格式）\n\n"
            "套餐价格：\n"
            f"{pricing_table}\n"
        )

        # 支持命令或回调两种入口
        if update.message:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        
        return SELECTING_PACKAGE
    
    @error_handler
    @log_action("Premium_选择套餐")
    async def package_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        用户选择套餐
        
        Args:
            update: Telegram 更新
            context: 上下文
            
        Returns:
            下一个对话状态
        """
        query = update.callback_query
        await query.answer()
        
        # 解析月数
        months = int(query.data.split('_')[1])
        context.user_data['premium_months'] = months
        context.user_data['base_amount'] = self.PACKAGES[months]
        
        await query.edit_message_text(
            f"✅ 已选择：{months} 个月 Premium\n\n"
            f"💰 价格：${self.PACKAGES[months]} USDT\n\n"
            f"📝 请发送收件人用户名（每行一个）：\n"
            f"支持格式：\n"
            f"  • @username\n"
            f"  • t.me/username\n"
            f"  • username\n\n"
            f"示例：\n"
            f"@alice\n"
            f"@bob\n"
            f"t.me/charlie",
            disable_web_page_preview=True
        )
        
        return ENTERING_RECIPIENTS
    
    @error_handler
    @log_action("Premium_输入收件人")
    async def recipients_entered(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        用户输入收件人
        
        Args:
            update: Telegram 更新
            context: 上下文
            
        Returns:
            下一个对话状态
        """
        text = update.message.text
        recipients = RecipientParser.parse(text)
        
        if not recipients:
            await update.message.reply_text(
                "❌ 未识别到有效用户名，请重新输入。\n\n"
                "支持格式：@username, t.me/username, username",
                disable_web_page_preview=True
            )
            return ENTERING_RECIPIENTS
        
        # 验证用户名格式
        invalid = [r for r in recipients if not RecipientParser.validate_username(r)]
        if invalid:
            await update.message.reply_text(
                f"❌ 以下用户名格式无效：\n{', '.join(invalid)}\n\n"
                f"请重新输入（用户名需 5-32 字符，仅字母、数字、下划线）"
            )
            return ENTERING_RECIPIENTS
        
        context.user_data['recipients'] = recipients
        
        # 创建订单
        try:
            base_amount = context.user_data['base_amount']
            order = await self.order_manager.create_order(
                user_id=update.effective_user.id,
                base_amount=base_amount,
                order_type=OrderType.PREMIUM,
                premium_months=context.user_data['premium_months'],
                recipients=recipients
            )
            if order is None:
                raise RuntimeError("failed to create order")

            context.user_data['order_id'] = order.order_id
            context.user_data['total_amount'] = order.total_amount
            context.user_data['unique_suffix'] = order.unique_suffix

        except Exception as e:
            logger.error(f"Failed to create premium order: {e}")
            await update.message.reply_text(
                "❌ 创建订单失败，请稍后重试或联系客服。"
            )
            return ConversationHandler.END
        
        # 确认订单
        keyboard = [
            [
                InlineKeyboardButton("✅ 确认支付", callback_data="confirm_payment"),
                InlineKeyboardButton("❌ 取消", callback_data="cancel_order")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        remaining_minutes = int((order.expires_at - order.created_at).total_seconds() / 60)

        await update.message.reply_text(
            f"📦 *订单确认*\n\n"
            f"套餐：{context.user_data['premium_months']} 个月 Premium\n"
            f"收件人数量：{len(recipients)}\n"
            f"收件人：{', '.join('@' + r for r in recipients[:5])}"
            f"{'...' if len(recipients) > 5 else ''}\n\n"
            f" 应付金额：`{context.user_data['total_amount']:.3f}` USDT (TRC20)\n"
            f" 收款地址：`{self.receive_address}`\n\n"
            f" 订单有效期：{remaining_minutes} 分钟\n"
            f" 订单号：`{order.order_id}`",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return CONFIRMING_PAYMENT
    
    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        用户确认支付
        
        Args:
            update: Telegram 更新
            context: 上下文
            
        Returns:
            对话结束
        """
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            f"✅ *订单已创建*\n\n"
            f"💰 应付金额：`{context.user_data['total_amount']:.3f}` USDT\n"
            f"📍 收款地址：`{self.receive_address}`\n\n"
            f"⚠️ 请精确转账 `{context.user_data['total_amount']:.3f}` USDT（包含小数部分）\n"
            f"⏰ 支付后 2-5 分钟内自动到账\n\n"
            f"🔖 订单号：`{context.user_data['order_id']}`\n"
            f"查询订单状态：/order_status {context.user_data['order_id']}",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    async def cancel_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        取消订单
        
        Args:
            update: Telegram 更新
            context: 上下文
            
        Returns:
            对话结束
        """
        query = update.callback_query
        await query.answer()
        
        # 释放后缀
        # 取消订单（内部会释放后缀）
        if 'order_id' in context.user_data:
            await self.order_manager.cancel_order(context.user_data['order_id'])
        
        await query.edit_message_text("❌ 订单已取消")
        
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        取消对话
        
        Args:
            update: Telegram 更新
            context: 上下文
            
        Returns:
            对话结束
        """
        await update.message.reply_text("操作已取消")
        
        # 清理资源：订单取消逻辑已在 cancel_order 中处理
        
        return ConversationHandler.END
    
    async def cancel_silent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        静默取消对话（用户点击其他菜单按钮时）
        
        Args:
            update: Telegram 更新
            context: 上下文
            
        Returns:
            对话结束
        """
        # 清除对话数据
        context.user_data.pop('premium_package_months', None)
        context.user_data.pop('premium_price', None)
        context.user_data.pop('premium_recipients', None)
        context.user_data.pop('premium_order_id', None)
        # 不显示取消消息，直接结束对话
        return ConversationHandler.END
