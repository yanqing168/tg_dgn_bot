"""TRX Exchange Handler - TRX/USDT Exchange with QR Code Payment."""

import logging
import string
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
import uuid

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..address_query.validator import AddressValidator
from .models import TRXExchangeOrder
# 从 legacy 导入业务逻辑类
from ..legacy.trx_exchange.rate_manager import RateManager
from ..legacy.trx_exchange.trx_sender import TRXSender
from src.common.settings_service import get_order_timeout_minutes

logger = logging.getLogger(__name__)

# Conversation states
INPUT_AMOUNT, INPUT_ADDRESS, SHOW_PAYMENT, CONFIRM_PAYMENT, INPUT_TX_HASH = range(5)


class TRXExchangeHandler:
    """Handle TRX Exchange (USDT → TRX)."""

    def __init__(self):
        """Initialize TRX exchange handler."""
        self.trx_sender = TRXSender()
        self.validator = AddressValidator()

    def generate_order_id(self) -> str:
        """Generate unique order ID."""
        return f"TRX{uuid.uuid4().hex[:16].upper()}"

    def generate_unique_amount(self, base_amount: Decimal) -> Decimal:
        """
        Generate unique amount with 3-decimal suffix.

        Args:
            base_amount: Base amount (e.g., Decimal('10'))

        Returns:
            Amount with unique suffix (e.g., Decimal('10.123'))
        """
        # Simple implementation: use random 3-digit suffix
        import random
        suffix = random.randint(1, 999)
        unique_amount = base_amount + Decimal(f"0.{suffix:03d}")
        return unique_amount

    async def start_exchange(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start TRX exchange flow."""
        await update.message.reply_text(
            "🔄 *TRX 闪兑*\n\n"
            "24小时自动兑换，安全快捷！\n\n"
            "💰 最低兑换：5 USDT\n"
            "💰 最高兑换：20,000 USDT\n"
            "⚡ 到账时间：5-10 分钟\n"
            "🔒 手续费：Bot 承担\n\n"
            "请输入您要兑换的 USDT 数量：",
            parse_mode="Markdown",
        )
        return INPUT_AMOUNT

    async def input_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle USDT amount input."""
        user_input = update.message.text.strip()

        # Validate amount
        try:
            amount = Decimal(user_input)
        except Exception:
            await update.message.reply_text(
                "❌ 金额格式错误，请输入数字（例如：10 或 10.5）"
            )
            return INPUT_AMOUNT

        # Check min/max limits
        if amount < Decimal("5"):
            await update.message.reply_text(
                f"❌ 最低兑换金额为 5 USDT\n请重新输入："
            )
            return INPUT_AMOUNT

        if amount > Decimal("20000"):
            await update.message.reply_text(
                f"❌ 最高兑换金额为 20,000 USDT\n请重新输入："
            )
            return INPUT_AMOUNT

        # Get current exchange rate
        db: Session = SessionLocal()
        try:
            rate = RateManager.get_rate(db)
            trx_amount = RateManager.calculate_trx_amount(amount, rate)
        finally:
            db.close()

        # Store in context
        context.user_data["exchange_usdt_amount"] = amount
        context.user_data["exchange_rate"] = rate
        context.user_data["exchange_trx_amount"] = trx_amount

        await update.message.reply_text(
            f"💱 *当前汇率*\n\n"
            f"1 USDT = {rate} TRX\n\n"
            f"📊 *兑换明细*\n"
            f"支付：{amount} USDT\n"
            f"获得：{trx_amount} TRX\n\n"
            f"请输入您的 TRX 接收地址：\n"
            f"（波场地址，T 开头，34 位）",
            parse_mode="Markdown",
        )
        return INPUT_ADDRESS

    async def input_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle TRX address input."""
        address = update.message.text.strip()

        # Validate address
        if not self.trx_sender.validate_address(address):
            await update.message.reply_text(
                "❌ 地址格式错误\n\n"
                "请输入有效的波场地址（T 开头，34 位）："
            )
            return INPUT_ADDRESS

        # Store address
        context.user_data["exchange_recipient_address"] = address

        # Show payment page
        return await self.show_payment(update, context)

    async def show_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show payment QR code and address."""
        user_id = update.effective_user.id
        usdt_amount = context.user_data["exchange_usdt_amount"]
        rate = context.user_data["exchange_rate"]
        trx_amount = context.user_data["exchange_trx_amount"]
        recipient_address = context.user_data["exchange_recipient_address"]

        # Create order with 3-decimal suffix
        db: Session = SessionLocal()
        now_utc = datetime.now(timezone.utc)
        timeout_minutes = get_order_timeout_minutes()
        expires_at = now_utc + timedelta(minutes=timeout_minutes)
        try:
            # Generate unique amount with suffix
            unique_amount = self.generate_unique_amount(usdt_amount)
            order_id = self.generate_order_id()

            # Create order in database
            order = TRXExchangeOrder(
                order_id=order_id,
                user_id=user_id,
                usdt_amount=unique_amount,
                trx_amount=trx_amount,
                exchange_rate=rate,
                recipient_address=recipient_address,
                payment_address=settings.trx_exchange_receive_address,
                status="PENDING",
                created_at=now_utc,
                expires_at=expires_at,
            )
            db.add(order)
            db.commit()

            logger.info(
                f"Created TRX exchange order: {order_id} "
                f"(user: {user_id}, USDT: {unique_amount}, TRX: {trx_amount})"
            )

        finally:
            db.close()

        # Store order_id in context
        context.user_data["exchange_order_id"] = order_id
        context.user_data.pop("exchange_order_pending", None)
        context.user_data.pop("exchange_confirmed", None)

        # Payment instruction message
        payment_address = settings.trx_exchange_receive_address
        qrcode_file_id = settings.trx_exchange_qrcode_file_id
        context.user_data["exchange_timeout_minutes"] = timeout_minutes
        logger.info(
            "TRX exchange order %s configured with timeout %s minutes (expires at %s)",
            order_id,
            timeout_minutes,
            expires_at.isoformat(),
        )

        message_text = (
            f"💳 *支付信息*\n\n"
            f"💰 支付金额：`{unique_amount}` USDT\n"
            f"📍 收款地址：\n<code>{payment_address}</code>\n\n"
            f"📊 *兑换信息*\n"
            f"🔄 兑换汇率：1 USDT = {rate} TRX\n"
            f"⚡ 获得数量：{trx_amount} TRX\n"
            f"📥 接收地址：<code>{recipient_address}</code>\n\n"
            f"⏰ *到账时间*\n"
            f"USDT 到账后 5-10 分钟内自动转账 TRX\n\n"
            f"⚠️ *温馨提示*\n"
            f"1. 请务必使用 TRC20-USDT 支付\n"
            f"2. 支付金额必须完全一致（包含 3 位小数）\n"
            f"3. 手续费由 Bot 承担，您无需额外支付\n"
            f"4. 订单有效期 {timeout_minutes} 分钟\n\n"
            f"💡 轻触地址即可复制到剪贴板"
        )

        # Send QR code image if available
        if qrcode_file_id and qrcode_file_id != "YOUR_QRCODE_FILE_ID_HERE":
            try:
                await update.effective_message.reply_photo(
                    photo=qrcode_file_id,
                    caption=message_text,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Failed to send QR code image: {e}")
                # Fallback to text only
                await update.effective_message.reply_text(
                    message_text,
                    parse_mode="HTML",
                )
        else:
            # No QR code configured, send text only
            await update.effective_message.reply_text(
                message_text,
                parse_mode="HTML",
            )

        await update.effective_message.reply_text(
            "✅ 支付完成后，请点击下方按钮确认：",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ 我已支付", callback_data=f"trx_paid_{order_id}")],
                [InlineKeyboardButton("❌ 取消兑换", callback_data=f"trx_cancel_{order_id}")],
            ]),
        )

        return CONFIRM_PAYMENT

    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle payment confirmation button."""
        query = update.callback_query
        await query.answer()

        data = query.data
        order_id = context.user_data.get("exchange_order_id")

        user_id = update.effective_user.id

        if data.startswith("trx_cancel_"):
            # 校验订单所有者
            cancel_order_id = data.replace("trx_cancel_", "")
            db: Session = SessionLocal()
            try:
                cancel_order = db.query(TRXExchangeOrder).filter_by(order_id=cancel_order_id).first()
                if cancel_order and cancel_order.user_id != user_id:
                    await query.answer("无权操作该订单", show_alert=True)
                    return CONFIRM_PAYMENT
            finally:
                db.close()

            await query.edit_message_text(
                "❌ 兑换已取消\n\n"
                "如需重新兑换，请使用 🔄 TRX 兑换 功能"
            )
            context.user_data.pop("exchange_order_id", None)
            context.user_data.pop("exchange_order_pending", None)
            context.user_data.pop("exchange_confirmed", None)
            return ConversationHandler.END

        if data.startswith("trx_paid_"):
            order_id = data.replace("trx_paid_", "")

            db: Session = SessionLocal()
            try:
                order = db.query(TRXExchangeOrder).filter_by(order_id=order_id).first()

                # H2 安全加固：校验订单所有者
                if order and order.user_id != user_id:
                    await query.answer("无权操作该订单", show_alert=True)
                    return CONFIRM_PAYMENT

                if (
                    order
                    and order.status == "PENDING"
                    and order.expires_at
                    and datetime.now(timezone.utc) > order.expires_at
                ):
                    order.status = "EXPIRED"
                    db.commit()
                    db.close()
                    await query.edit_message_text(
                        "❌ 订单已过期，请重新发起兑换。",
                    )
                    context.user_data.pop("exchange_order_id", None)
                    context.user_data.pop("exchange_order_pending", None)
                    context.user_data.pop("exchange_confirmed", None)
                    return ConversationHandler.END
            finally:
                db.close()

            if not order:
                await query.edit_message_text("❌ 未找到兑换订单，请重新开始流程。")
                return ConversationHandler.END

            if order.status != "PENDING" or context.user_data.get("exchange_confirmed"):
                await query.edit_message_text(
                    "✅ 订单已记录，正在等待后台审核。如需加速，请联系客服并提供订单号。",
                    parse_mode="HTML",
                )
                return ConversationHandler.END

            context.user_data["exchange_order_pending"] = order_id

            await query.edit_message_text(
                "✅ <b>我们已收到您的支付确认</b>\n\n"
                "为了加速核验，请发送本次转账的 TX Hash：\n"
                "• 在钱包/交易记录中复制 64 位哈希（可含 0x 前缀）\n"
                "• 如暂时无法提供，可输入 <code>跳过</code> 或 <code>skip</code>\n\n"
                "ℹ️ 详细教程见 /help → 支付充值",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
                ),
            )

            return INPUT_TX_HASH

        return CONFIRM_PAYMENT

    async def handle_tx_hash_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle user TX hash input after payment confirmation."""
        message = update.message
        order_id = context.user_data.get("exchange_order_pending")
        back_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("� 返回主菜单", callback_data="back_to_main")]]
        )

        if not order_id:
            await message.reply_text(
                "❌ 未找到兑换订单，请重新开始流程。",
                parse_mode="HTML",
                reply_markup=back_markup,
            )
            return ConversationHandler.END

        user_input = (message.text or "").strip()
        lower = user_input.lower()

        if lower in {"跳过", "skip"}:
            tx_hash: str | None = None
        else:
            normalized = lower[2:] if lower.startswith("0x") else lower
            if len(normalized) != 64 or any(ch not in string.hexdigits for ch in normalized):
                await message.reply_text(
                    "❌ TX Hash 格式不正确，请重新输入 64 位十六进制字符串，或回复 <code>跳过</code>。",
                    parse_mode="HTML",
                )
                return INPUT_TX_HASH
            tx_hash = user_input

        saved = self._store_tx_hash_placeholder(order_id, tx_hash)
        context.user_data["exchange_confirmed"] = True
        context.user_data.pop("exchange_order_pending", None)

        if tx_hash:
            await self._trigger_verifier(order_id, tx_hash)

        confirmation = (
            "✅ <b>支付信息已记录</b>\n\n"
            "我们会尽快核验链上记录并完成 TRX 转账。\n"
            "如需人工协助，请提供订单号与 TX Hash 联系客服。"
        )
        if not saved:
            confirmation += "\n\n⚠️ 暂未写入后台记录，请稍后联系客服补充信息。"

        await message.reply_text(
            confirmation,
            parse_mode="HTML",
            reply_markup=back_markup,
        )

        return ConversationHandler.END

    def _store_tx_hash_placeholder(self, order_id: str, tx_hash: str | None) -> bool:
        db = SessionLocal()
        try:
            order = db.query(TRXExchangeOrder).filter_by(order_id=order_id).first()
            if not order:
                logger.warning("TRX exchange order not found for TX hash placeholder: %s", order_id)
                return False

            note = "USER_CONFIRMED_SKIP" if tx_hash is None else f"USER_TX_HASH::{tx_hash}"
            existing = order.error_message or ""
            order.error_message = note if not existing else f"{note}\n{existing}"
            db.commit()
            return True
        except Exception as exc:
            logger.error("Failed to store TX hash placeholder for %s: %s", order_id, exc)
            db.rollback()
            return False
        finally:
            db.close()

    async def _trigger_verifier(self, order_id: str, tx_hash: str) -> None:
        try:
            logger.info("[TRXExchange] pending verification for %s with %s", order_id, tx_hash)
        except Exception as exc:
            logger.warning("TRX order %s verification placeholder failed: %s", order_id, exc)

    async def handle_payment_callback(self, order_id: str) -> None:
        """
        Handle TRC20 payment callback for TRX exchange.

        Called by TRC20Handler when payment is confirmed.

        Args:
            order_id: TRX exchange order ID
        """
        db: Session = SessionLocal()
        try:
            # Get order
            order = db.query(TRXExchangeOrder).filter_by(order_id=order_id).first()

            if not order:
                logger.error(f"TRX exchange order not found: {order_id}")
                return

            if (
                order.status == "PENDING"
                and order.expires_at
                and datetime.now(timezone.utc) > order.expires_at
            ):
                order.status = "EXPIRED"
                db.commit()
                logger.warning("TRX exchange order %s expired before payment callback", order_id)
                return

            if order.status != "PENDING":
                logger.warning(f"Order already processed: {order_id} (status: {order.status})")
                return

            # Update order status
            order.status = "PAID"
            order.paid_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"TRX exchange order paid: {order_id}")

            # Send TRX
            try:
                tx_hash = self.trx_sender.send_trx(
                    recipient_address=order.recipient_address,
                    amount=order.trx_amount,
                    order_id=order_id,
                )

                # Update order status
                order.status = "TRANSFERRED"
                order.tx_hash = tx_hash
                order.transferred_at = datetime.now(timezone.utc)
                db.commit()

                logger.info(
                    f"TRX transferred: {order.trx_amount} TRX → {order.recipient_address} "
                    f"(order: {order_id}, tx: {tx_hash})"
                )

                # TODO: Notify user about successful transfer
                # This requires bot instance in context

            except Exception as e:
                logger.error(f"TRX transfer failed (order: {order_id}): {e}", exc_info=True)
                order.status = "FAILED"
                db.commit()

                # TODO: Notify admin about failed transfer

        finally:
            db.close()

    def get_handlers(self):
        """Get conversation handlers for TRX exchange."""
        return ConversationHandler(
            entry_points=[
                # Reply按钮入口
                MessageHandler(filters.Regex("^🔄 TRX 兑换$"), self.start_exchange),
                # Inline按钮入口
                CallbackQueryHandler(self.start_exchange, pattern="^menu_trx_exchange$"),
            ],
            states={
                INPUT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_amount)],
                INPUT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_address)],
                CONFIRM_PAYMENT: [CallbackQueryHandler(self.confirm_payment, pattern="^trx_(paid|cancel)_")],
                INPUT_TX_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_tx_hash_input)],
            },
            fallbacks=[
                CommandHandler("cancel", self._cancel),
                CallbackQueryHandler(self._cancel, pattern="^(menu_premium|menu_profile|menu_address_query|menu_energy|menu_clone|menu_support|back_to_main)$"),
            ],
            name="trx_exchange",
            persistent=False,
            allow_reentry=True,
            per_chat=True,
            per_user=True,
            per_message=False,
        )

    async def _cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel conversation - supports both message and callback_query."""
        # 清理用户数据
        context.user_data.clear()
        
        # 根据update类型发送响应
        if update.callback_query:
            await update.callback_query.answer("已取消")
            try:
                await update.callback_query.edit_message_text(
                    "❌ 操作已取消\n\n"
                    "如需重新兑换，请使用 🔄 TRX 兑换 功能"
                )
            except Exception:
                # 如果编辑失败，发送新消息
                await update.effective_message.reply_text(
                    "❌ 操作已取消\n\n"
                    "如需重新兑换，请使用 🔄 TRX 兑换 功能"
                )
        elif update.message:
            await update.message.reply_text(
                "❌ 操作已取消\n\n"
                "如需重新兑换，请使用 🔄 TRX 兑换 功能"
            )
        else:
            # 其他类型的update
            if update.effective_message:
                await update.effective_message.reply_text("❌ 操作已取消")
        
        return ConversationHandler.END
