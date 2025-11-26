"""
能量兑换 Bot 处理器（TRX/USDT 直转模式）
用户直接转账到代理地址，后台自动处理订单
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
import logging
import string
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy.exc import SQLAlchemyError

# 从 legacy 导入业务逻辑类
from ..legacy.energy.models import EnergyPackage, EnergyOrderType

logger = logging.getLogger(__name__)
from ..address_query.validator import AddressValidator
from ..config import settings
from ..database import SessionLocal, EnergyOrder as DBEnergyOrder
from src.common.settings_service import get_order_timeout_minutes


# 对话状态
STATE_SELECT_TYPE = 1
STATE_SELECT_PACKAGE = 2
STATE_INPUT_ADDRESS = 3
STATE_INPUT_COUNT = 4
STATE_SHOW_PAYMENT = 5
STATE_INPUT_USDT = 6
STATE_INPUT_TX_HASH = 7


class EnergyPaymentVerifier:
    """链上校验占位，后续可接入真实节点/API"""

    @staticmethod
    async def verify(order_id: str, tx_hash: str) -> None:
        """占位实现：当前仅记录日志，后续接入链上校验"""
        logger.info(
            "[EnergyPaymentVerifier] pending verification for order %s with tx %s",
            order_id,
            tx_hash,
        )


class EnergyDirectHandler:
    """能量兑换处理器（直转模式）"""

    @staticmethod
    def _get_timeout_minutes(context: ContextTypes.DEFAULT_TYPE) -> int:
        timeout = context.user_data.get("energy_timeout_minutes")
        if timeout is None:
            timeout = get_order_timeout_minutes()
            context.user_data["energy_timeout_minutes"] = timeout
        return timeout
    
    async def start_energy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始能量兑换流程（兼容 CallbackQuery 和 Message 两种入口）"""
        # 兼容 CallbackQuery（inline 按钮）和 Message（Reply 按钮）两种入口
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            send_method = query.edit_message_text
        else:
            # Reply 按钮入口
            send_method = update.message.reply_text
        
        keyboard = [
            [InlineKeyboardButton("⚡ 时长能量（闪租）", callback_data="energy_type_hourly")],
            [InlineKeyboardButton("📦 笔数套餐", callback_data="energy_type_package")],
            [InlineKeyboardButton("🔄 闪兑", callback_data="energy_type_flash")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        timeout_minutes = self._get_timeout_minutes(context)
        text = (
            "⚡ <b>能量兑换服务</b>\n\n"
            "选择兑换类型：\n\n"
            "⚡ <b>时长能量（闪租）</b>\n"
            "  • 6.5万能量 = 3 TRX\n"
            "  • 13.1万能量 = 6 TRX\n"
            "  • 有效期：1小时\n"
            "  • 支付方式：TRX 转账\n"
            "  • 6秒到账\n\n"
            "📦 <b>笔数套餐</b>\n"
            "  • 弹性笔数：有U扣1笔，无U扣2笔\n"
            "  • 起售金额：5 USDT\n"
            "  • 支付方式：USDT 转账\n"
            "  • 每天至少使用一次\n\n"
            "🔄 <b>闪兑</b>\n"
            "  • USDT 直接兑换能量\n"
            "  • 支付方式：USDT 转账\n"
            "  • 即时到账\n\n"
            f"⏰ 订单有效期：{timeout_minutes} 分钟"
        )
        
        await send_method(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        return STATE_SELECT_TYPE
    
    async def select_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """选择能量类型"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "energy_type_hourly":
            # 时长能量（闪租） -> 选择套餐
            context.user_data["energy_type"] = EnergyOrderType.HOURLY
            return await self.select_package(update, context)
            
        elif data == "energy_type_package":
            # 笔数套餐 -> 输入地址
            context.user_data["energy_type"] = EnergyOrderType.PACKAGE
            
            timeout_minutes = self._get_timeout_minutes(context)
            text = (
                "📦 <b>笔数套餐购买</b>\n\n"
                "请输入接收能量的波场地址：\n\n"
                "⚠️ 注意：\n"
                "• 必须是有效的波场地址（T开头）\n"
                "• 最低充值：5 USDT\n"
                "• 每笔约0.5 USDT\n"
                f"• 订单有效期：{timeout_minutes} 分钟\n\n"
                "示例: <code>TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH</code>"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="energy_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            return STATE_INPUT_ADDRESS
            
        elif data == "energy_type_flash":
            # 闪兑 -> 输入地址
            context.user_data["energy_type"] = EnergyOrderType.FLASH
            
            timeout_minutes = self._get_timeout_minutes(context)
            text = (
                "🔄 <b>闪兑购买</b>\n\n"
                "请输入接收能量的波场地址：\n\n"
                "⚠️ 注意：\n"
                "• 必须是有效的波场地址（T开头）\n"
                "• USDT 直接兑换能量\n"
                "• 即时到账\n"
                f"• 订单有效期：{timeout_minutes} 分钟\n\n"
                "示例: <code>TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH</code>"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="energy_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            return STATE_INPUT_ADDRESS
        
        return STATE_SELECT_TYPE
    
    async def select_package(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """选择能量套餐"""
        query = update.callback_query
        
        keyboard = [
            [InlineKeyboardButton("⚡ 6.5万能量 (3 TRX)", callback_data="package_65000")],
            [InlineKeyboardButton("⚡ 13.1万能量 (6 TRX)", callback_data="package_131000")],
            [InlineKeyboardButton("🔙 返回", callback_data="energy_start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        timeout_minutes = self._get_timeout_minutes(context)
        text = (
            "⚡ <b>选择能量套餐</b>\n\n"
            "请选择购买的能量数量：\n\n"
            "💡 说明：\n"
            "• 有效期：1小时\n"
            "• 6秒到账\n"
            "• TRX 转账支付\n"
            "• 下一步将输入购买笔数（1-20）\n\n"
            f"⏰ 订单有效期：{timeout_minutes} 分钟"
        )
        
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        return STATE_SELECT_PACKAGE
    
    async def input_count(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """输入购买笔数"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "package_65000":
            context.user_data["energy_package"] = EnergyPackage.SMALL
            unit_price = 3
        elif data == "package_131000":
            context.user_data["energy_package"] = EnergyPackage.LARGE
            unit_price = 6
        else:
            return STATE_SELECT_PACKAGE
        
        timeout_minutes = self._get_timeout_minutes(context)
        text = (
            f"⚡ <b>购买笔数</b>\n\n"
            f"已选套餐：{context.user_data['energy_package'].value} 能量\n"
            f"单价：{unit_price} TRX/笔\n\n"
            f"请输入购买笔数（1-20）：\n\n"
            f"💡 示例：\n"
            f"• 输入 5 = {unit_price * 5} TRX\n"
            f"• 输入 10 = {unit_price * 10} TRX\n"
            f"• 输入 20 = {unit_price * 20} TRX\n\n"
            f"⏰ 订单有效期：{timeout_minutes} 分钟"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="energy_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        return STATE_INPUT_COUNT
    
    async def input_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """输入接收地址"""
        message = update.message
        energy_type = context.user_data.get("energy_type")
        
        # 如果是时长能量，先验证笔数
        if energy_type == EnergyOrderType.HOURLY:
            try:
                count = int(message.text.strip())
                if count < 1 or count > 20:
                    await message.reply_text(
                        "❌ 购买笔数必须在 1-20 之间，请重新输入："
                    )
                    return STATE_INPUT_COUNT
                
                context.user_data["purchase_count"] = count
                
            except ValueError:
                await message.reply_text(
                    "❌ 请输入有效的数字（1-20）："
                )
                return STATE_INPUT_COUNT
            
            # 计算价格
            package = context.user_data["energy_package"]
            unit_price = 3 if package == EnergyPackage.SMALL else 6
            total_price = unit_price * count
            
            text = (
                f"📍 <b>接收地址</b>\n\n"
                f"套餐：{package.value} 能量\n"
                f"笔数：{count} 笔\n"
                f"总价：{total_price} TRX (约{total_price / 7:.2f} USDT)\n\n"
                f"请输入接收能量的波场地址：\n\n"
                f"⚠️ 注意：\n"
                f"• 必须是有效的波场地址（T开头）\n"
                f"• 能量将发送到此地址\n"
                f"• 1小时内有效\n\n"
                f"示例: <code>TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH</code>"
            )
            
            await message.reply_text(text, parse_mode="HTML")
            return STATE_INPUT_ADDRESS
        
        # 笔数套餐和闪兑：直接等待地址输入
        else:
            # 这里是等待地址输入的状态，不需要额外处理
            return STATE_INPUT_ADDRESS
    
    async def show_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """显示支付信息"""
        message = update.message
        address = message.text.strip()
        
        # 验证地址
        is_valid, error_msg = AddressValidator.validate(address)
        if not is_valid:
            await message.reply_text(
                f"❌ {error_msg}\n\n"
                "请重新输入正确的波场地址"
            )
            return STATE_INPUT_ADDRESS
        
        context.user_data["receive_address"] = address
        energy_type = context.user_data["energy_type"]
        reply_markup: InlineKeyboardMarkup
        total_price_trx = None
        total_price_usdt = None

        timeout_minutes = get_order_timeout_minutes()

        if energy_type == EnergyOrderType.HOURLY:
            package = context.user_data["energy_package"]
            count = context.user_data["purchase_count"]
            unit_price = 3 if package == EnergyPackage.SMALL else 6
            total_price_trx = unit_price * count
            proxy_address = settings.energy_rent_address
            if not proxy_address:
                await message.reply_text(
                    "❌ <b>系统错误</b>\n\n能量闪租地址未配置，请联系管理员",
                    parse_mode="HTML",
                )
                return ConversationHandler.END

            text = (
                f"💳 <b>支付信息</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 套餐：{package.value} 能量\n"
                f"🔢 笔数：{count} 笔\n"
                f"📍 接收地址：\n<code>{address}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>支付金额：{total_price_trx} TRX</b>\n\n"
                f"🔗 <b>收款地址：</b>\n<code>{proxy_address}</code>\n\n"
                f"⚠️ <b>重要提示：</b>\n"
                f"• 请转账 <b>整数金额</b>（{total_price_trx} TRX）\n"
                f"• 转账后 <b>6秒自动到账</b>\n"
                f"• 能量有效期：<b>1小时</b>\n"
                f"• 请在 {timeout_minutes} 分钟内完成支付\n"
                f"• 请勿重复转账\n\n"
                f"💡 如有问题请联系客服"
            )

        elif energy_type == EnergyOrderType.PACKAGE:
            proxy_address = settings.energy_package_address
            if not proxy_address:
                await message.reply_text(
                    "❌ <b>系统错误</b>\n\n笔数套餐地址未配置，请联系管理员",
                    parse_mode="HTML",
                )
                return ConversationHandler.END

            text = (
                f"💳 <b>支付信息</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 笔数套餐\n"
                f"📍 接收地址：\n<code>{address}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>支付金额：自定义（最低 5 USDT）</b>\n\n"
                f"🔗 <b>收款地址（USDT TRC20）：</b>\n<code>{proxy_address}</code>\n\n"
                f"⚠️ <b>重要提示：</b>\n"
                f"• 请转账 <b>整数金额</b>（如：5、10、20 USDT）\n"
                f"• 最低充值：<b>5 USDT</b>\n"
                f"• 每笔约 0.5 USDT\n"
                f"• 弹性扣费：有U扣1笔，无U扣2笔\n"
                f"• 每天至少使用一次\n"
                f"• 请在 {timeout_minutes} 分钟内完成支付\n\n"
                f"💡 如有问题请联系客服"
            )

        elif energy_type == EnergyOrderType.FLASH:
            proxy_address = settings.energy_flash_address
            if not proxy_address:
                await message.reply_text(
                    "❌ <b>系统错误</b>\n\n闪兑地址未配置，请联系管理员",
                    parse_mode="HTML",
                )
                return ConversationHandler.END

            text = (
                f"💳 <b>支付信息</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔄 闪兑\n"
                f"📍 接收地址：\n<code>{address}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>支付金额：自定义</b>\n\n"
                f"🔗 <b>收款地址（USDT TRC20）：</b>\n<code>{proxy_address}</code>\n\n"
                f"⚠️ <b>重要提示：</b>\n"
                f"• 请转账 <b>整数金额</b>（如：10、20、50 USDT）\n"
                f"• USDT 直接兑换能量\n"
                f"• 即时到账\n"
                f"• 请在 {timeout_minutes} 分钟内完成支付\n\n"
                f"💡 如有问题请联系客服"
            )

        else:
            return ConversationHandler.END

        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ 我已转账", callback_data="payment_done")],
                [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")],
            ]
        )

        self._ensure_energy_order_record(
            context=context,
            user_id=update.effective_user.id,
            energy_type=energy_type,
            receive_address=address,
            total_price_trx=total_price_trx,
            total_price_usdt=total_price_usdt,
        )

        await message.reply_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
        return STATE_SHOW_PAYMENT
    
    async def payment_done(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """用户确认已转账"""
        query = update.callback_query
        await query.answer()

        order_id = context.user_data.get("energy_order_id")
        if not order_id:
            order_id = getattr(context, "_energy_pending_order_id", None)
        back_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
        )

        if context.user_data.get("energy_confirmed"):
            await query.edit_message_text(
                text="✅ 订单已记录，正在等待后台审核。若需加速处理，可联系人工客服并提供订单号。",
                reply_markup=back_markup,
                parse_mode="HTML",
            )
            return ConversationHandler.END

        if not order_id:
            order_id = getattr(context, "_energy_pending_order_id", None)

        energy_type = context.user_data.get("energy_type")
        if not energy_type:
            pending_type = getattr(context, "_energy_pending_type", None)
            if pending_type:
                try:
                    energy_type = EnergyOrderType(pending_type)
                except ValueError:
                    energy_type = None
        wait_time = "6秒" if energy_type == EnergyOrderType.HOURLY else "几分钟"

        timeout_minutes = get_order_timeout_minutes()
        instruction = (
            "✅ <b>我们已记录您的支付确认</b>\n\n"
            f"⏰ 预计到账时间：{wait_time}\n"
            f"⏰ 订单有效期：{timeout_minutes} 分钟\n"
            "ℹ️ 详细教程见 /help → 支付充值\n\n"
            "为了加速核验，请发送本次转账的 TX Hash：\n"
            "• 在钱包/交易记录中复制 64 位哈希（可含 0x 前缀）\n"
            "• 如暂时无法提供，可输入 <code>跳过</code> 或 <code>skip</code>"
        )

        await query.edit_message_text(
            text=instruction,
            reply_markup=back_markup,
            parse_mode="HTML",
        )

        setattr(context, "_energy_pending_order_id", order_id)
        setattr(context, "_energy_pending_type", energy_type.value if energy_type else None)
        self._clear_energy_context(context)

        return STATE_INPUT_TX_HASH
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消操作 - 使用统一清理机制"""
        from src.common.navigation_manager import NavigationManager
        
        # 先发送取消确认
        if update.callback_query:
            await update.callback_query.answer("已取消")
        
        # 清理能量模块特定的上下文
        self._clear_energy_context(context)
        
        # 使用统一的清理和导航方法
        return await NavigationManager.cleanup_and_show_main_menu(update, context)
    
    async def handle_energy_tx_hash_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """接收用户输入的 TX Hash 或跳过指令"""
        message = update.message
        order_id = context.user_data.get("energy_order_id")
        back_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
        )

        if not order_id:
            await message.reply_text(
                "❌ 未找到关联订单，请重新开始能量兑换。",
                reply_markup=back_markup,
                parse_mode="HTML",
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
                return STATE_INPUT_TX_HASH
            tx_hash = user_input

        saved = self._store_tx_hash_placeholder(order_id, tx_hash)
        context.user_data["energy_confirmed"] = True
        context.user_data.pop("awaiting_tx_hash", None)

        if tx_hash:
            await self._trigger_verifier(order_id, tx_hash)

        confirmation_text = (
            "✅ <b>支付信息已记录</b>\n\n"
            "我们会尽快核验链上记录并完成能量下发。\n"
            "如需人工协助，请提供订单号与 TX Hash 联系客服。"
        )
        if not saved:
            confirmation_text += "\n\n⚠️ 暂未写入后台记录，请稍后联系客服补充信息。"

        await message.reply_text(
            confirmation_text,
            reply_markup=back_markup,
            parse_mode="HTML",
        )

        self._clear_energy_context(context)
        setattr(context, "_energy_pending_order_id", None)
        setattr(context, "_energy_pending_type", None)
        return ConversationHandler.END

    async def cancel_silent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """静默取消操作（用户点击其他菜单按钮时）"""
        self._clear_energy_context(context)
        # 不显示取消消息，直接结束对话
        return ConversationHandler.END

    def _ensure_energy_order_record(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        energy_type: EnergyOrderType,
        receive_address: str,
        total_price_trx: float | None,
        total_price_usdt: float | None,
    ) -> str | None:
        existing = context.user_data.get("energy_order_id")
        if existing:
            return existing

        now_utc = datetime.now(timezone.utc)
        order_id = f"ENRG-{user_id}-{int(now_utc.timestamp())}-{uuid.uuid4().hex[:6].upper()}"
        timeout_minutes = get_order_timeout_minutes()
        db = SessionLocal()
        try:
            db_order = DBEnergyOrder(
                order_id=order_id,
                user_id=user_id,
                order_type=energy_type.value,
                energy_amount=int(context.user_data.get("energy_package", EnergyPackage.SMALL).value)
                if energy_type == EnergyOrderType.HOURLY
                else None,
                purchase_count=context.user_data.get("purchase_count"),
                receive_address=receive_address,
                total_price_trx=total_price_trx,
                total_price_usdt=total_price_usdt,
                status="PENDING",
                created_at=now_utc,
            )
            db.add(db_order)
            db.commit()
            logger.info("创建能量订单记录 %s (type=%s)", order_id, energy_type.value)
        except SQLAlchemyError as exc:
            logger.error("创建能量订单记录失败: %s", exc)
            order_id = None
            db.rollback()
        finally:
            db.close()

        if order_id:
            context.user_data["energy_order_id"] = order_id
        return order_id

    def _store_tx_hash_placeholder(self, order_id: str, tx_hash: str | None) -> bool:
        db = SessionLocal()
        try:
            db_order = db.query(DBEnergyOrder).filter_by(order_id=order_id).first()
            if not db_order:
                logger.warning("未找到订单 %s，无法记录 TX Hash", order_id)
                return False
            note = "USER_CONFIRMED_SKIP" if tx_hash is None else f"USER_TX_HASH::{tx_hash}"
            existing = db_order.error_message or ""
            db_order.error_message = note if not existing else f"{note}\n{existing}"
            db.commit()
            return True
        except SQLAlchemyError as exc:
            logger.error("记录 TX Hash 占位失败: %s", exc)
            db.rollback()
            return False
        finally:
            db.close()

    async def _trigger_verifier(self, order_id: str, tx_hash: str) -> None:
        try:
            await EnergyPaymentVerifier.verify(order_id, tx_hash)
        except Exception as exc:
            logger.warning("能量订单 %s 链上校验占位失败: %s", order_id, exc)

    def _clear_energy_context(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        for key in [
            "energy_type",
            "energy_package",
            "purchase_count",
            "receive_address",
            "energy_order_id",
            "awaiting_tx_hash",
            "energy_confirmed",
        ]:
            context.user_data.pop(key, None)

def create_energy_direct_handler() -> ConversationHandler:
    """创建能量兑换对话处理器（直转模式）"""
    handler_instance = EnergyDirectHandler()
    
    return ConversationHandler(
        entry_points=[
            # Inline 按钮入口：menu_energy
            CallbackQueryHandler(handler_instance.start_energy, pattern="^menu_energy$"),
            # Reply 按钮入口：⚡ 能量兑换
            MessageHandler(filters.Regex(r"^⚡ 能量兑换$"), handler_instance.start_energy),
        ],
        states={
            STATE_SELECT_TYPE: [
                CallbackQueryHandler(handler_instance.select_type, pattern="^energy_type_"),
            ],
            STATE_SELECT_PACKAGE: [
                CallbackQueryHandler(handler_instance.input_count, pattern="^package_"),
            ],
            STATE_INPUT_COUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler_instance.input_address),
            ],
            STATE_INPUT_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler_instance.show_payment),
            ],
            STATE_SHOW_PAYMENT: [
                CallbackQueryHandler(handler_instance.payment_done, pattern="^payment_done$"),
            ],
            STATE_INPUT_TX_HASH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler_instance.handle_energy_tx_hash_input),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(handler_instance.start_energy, pattern="^energy_start$"),
            CallbackQueryHandler(handler_instance.cancel, pattern="^back_to_main$"),
            # 当用户点击其他功能按钮时，自动结束当前对话
            CallbackQueryHandler(handler_instance.cancel_silent, pattern="^(menu_premium|menu_profile|menu_address_query|menu_clone|menu_support)$"),
        ],
        name="energy_direct_handler",
        persistent=False,
        allow_reentry=True,
        per_chat=True,
        per_user=True,
        per_message=False,
    )
