"""
能量兑换 Bot 处理器
处理用户交互和对话流程
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
from loguru import logger

# 从 legacy 导入业务逻辑类
from ..legacy.energy.manager import EnergyOrderManager
from ..legacy.energy.models import EnergyPackage, EnergyOrderType
from ..address_query.validator import AddressValidator


# 对话状态
STATE_SELECT_TYPE = 1
STATE_SELECT_PACKAGE = 2
STATE_INPUT_ADDRESS = 3
STATE_INPUT_COUNT = 4
STATE_CONFIRM = 5
STATE_INPUT_USDT = 6


class EnergyHandler:
    """能量兑换处理器"""
    
    def __init__(self, order_manager: EnergyOrderManager):
        """
        初始化处理器
        
        Args:
            order_manager: 订单管理器
        """
        self.manager = order_manager
    
    async def start_energy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始能量兑换流程"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("⚡ 时长能量（1小时）", callback_data="energy_type_hourly")],
            [InlineKeyboardButton("📦 笔数套餐", callback_data="energy_type_package")],
            [InlineKeyboardButton("🔄 闪兑", callback_data="energy_type_flash")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "⚡ <b>能量兑换服务</b>\n\n"
            "选择兑换类型：\n\n"
            "⚡ <b>时长能量</b>\n"
            "  • 6.5万能量 = 3 TRX\n"
            "  • 13.1万能量 = 6 TRX\n"
            "  • 有效期：1小时\n"
            "  • 最多购买：1-20笔\n\n"
            "📦 <b>笔数套餐</b>\n"
            "  • 弹性笔数：有U扣1笔，无U扣2笔\n"
            "  • 每笔价格：3.6 TRX\n"
            "  • 起售金额：5 USDT\n"
            "  • 每天至少使用一次\n\n"
            "🔄 <b>闪兑</b>\n"
            "  • USDT 直接兑换能量\n"
            "  • 即时到账"
        )
        
        await query.edit_message_text(
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
            # 时长能量 -> 选择套餐
            context.user_data["energy_type"] = EnergyOrderType.HOURLY
            return await self.select_package(update, context)
            
        elif data == "energy_type_package":
            # 笔数套餐 -> 输入USDT金额
            context.user_data["energy_type"] = EnergyOrderType.PACKAGE
            
            text = (
                "📦 <b>笔数套餐购买</b>\n\n"
                "请输入充值金额（USDT）：\n\n"
                "💡 说明：\n"
                "• 最低充值：5 USDT\n"
                "• 每笔价格：3.6 TRX（约0.5 USDT）\n"
                "• 弹性扣费：有U扣1笔，无U扣2笔\n"
                "• 每天至少使用一次，否则扣2笔\n\n"
                "示例：充值 10 USDT 约可获得 140 笔"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="energy_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            return STATE_INPUT_USDT
            
        elif data == "energy_type_flash":
            # 闪兑（暂未实现）
            await query.edit_message_text(
                text="🔄 <b>闪兑功能</b>\n\n🚧 功能开发中，敬请期待...",
                parse_mode="HTML"
            )
            return ConversationHandler.END
        
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
        
        text = (
            "⚡ <b>选择能量套餐</b>\n\n"
            "请选择购买的能量数量：\n\n"
            "💡 说明：\n"
            "• 有效期：1小时\n"
            "• 自动到账\n"
            "• 下一步将输入购买笔数（1-20）"
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
            unit_price = 3.0
        elif data == "package_131000":
            context.user_data["energy_package"] = EnergyPackage.LARGE
            unit_price = 6.0
        else:
            return STATE_SELECT_PACKAGE
        
        text = (
            f"⚡ <b>购买笔数</b>\n\n"
            f"已选套餐：{context.user_data['energy_package'].value} 能量\n"
            f"单价：{unit_price} TRX/笔\n\n"
            f"请输入购买笔数（1-20）：\n\n"
            f"💡 示例：\n"
            f"• 输入 5 = {unit_price * 5} TRX\n"
            f"• 输入 10 = {unit_price * 10} TRX\n"
            f"• 输入 20 = {unit_price * 20} TRX"
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
        
        # 验证笔数输入
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
        unit_price = 3.0 if package == EnergyPackage.SMALL else 6.0
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
            f"• 1小时内有效"
        )
        
        await message.reply_text(text, parse_mode="HTML")
        
        return STATE_INPUT_ADDRESS
    
    async def confirm_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """确认订单"""
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
        
        # 获取订单信息
        energy_type = context.user_data["energy_type"]
        
        if energy_type == EnergyOrderType.HOURLY:
            package = context.user_data["energy_package"]
            count = context.user_data["purchase_count"]
            unit_price = 3.0 if package == EnergyPackage.SMALL else 6.0
            total_price = unit_price * count
            
            text = (
                f"✅ <b>订单确认</b>\n\n"
                f"📦 套餐：{package.value} 能量\n"
                f"🔢 笔数：{count} 笔\n"
                f"📍 地址：<code>{address}</code>\n"
                f"💰 总价：{total_price} TRX (约{total_price / 7:.2f} USDT)\n"
                f"⏰ 有效期：1小时\n\n"
                f"确认购买吗？"
            )
            
        elif energy_type == EnergyOrderType.PACKAGE:
            usdt_amount = context.user_data.get("usdt_amount", 0)
            estimated_count = int(usdt_amount * 7 / 3.6)
            
            text = (
                f"✅ <b>订单确认</b>\n\n"
                f"📦 笔数套餐\n"
                f"💰 金额：{usdt_amount} USDT\n"
                f"📍 地址：<code>{address}</code>\n"
                f"🔢 预计笔数：约{estimated_count}笔\n\n"
                f"💡 说明：\n"
                f"• 弹性扣费：有U扣1笔，无U扣2笔\n"
                f"• 每天至少使用一次\n\n"
                f"确认购买吗？"
            )
        else:
            return ConversationHandler.END
        
        keyboard = [
            [
                InlineKeyboardButton("✅ 确认购买", callback_data="energy_confirm_yes"),
                InlineKeyboardButton("❌ 取消", callback_data="energy_confirm_no"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        return STATE_CONFIRM
    
    async def process_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理订单"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "energy_confirm_no":
            await query.edit_message_text(
                text="❌ 已取消订单"
            )
            return ConversationHandler.END
        
        if data != "energy_confirm_yes":
            return STATE_CONFIRM
        
        # 创建订单
        user_id = update.effective_user.id
        energy_type = context.user_data["energy_type"]
        receive_address = context.user_data["receive_address"]
        
        try:
            await query.edit_message_text(
                text="⏳ 正在创建订单..."
            )
            
            if energy_type == EnergyOrderType.HOURLY:
                # 时长能量订单
                package = context.user_data["energy_package"]
                count = context.user_data["purchase_count"]
                
                order = await self.manager.create_hourly_order(
                    user_id=user_id,
                    receive_address=receive_address,
                    energy_package=package,
                    purchase_count=count
                )
                
            elif energy_type == EnergyOrderType.PACKAGE:
                # 笔数套餐订单
                usdt_amount = context.user_data["usdt_amount"]
                
                order = await self.manager.create_package_order(
                    user_id=user_id,
                    receive_address=receive_address,
                    usdt_amount=usdt_amount
                )
            
            else:
                raise ValueError("不支持的订单类型")
            
            # 使用余额支付
            success, error = await self.manager.pay_with_balance(order.order_id)
            
            if not success:
                await query.edit_message_text(
                    text=f"❌ <b>支付失败</b>\n\n{error or '未知错误'}\n\n请检查余额或联系客服",
                    parse_mode="HTML"
                )
                return ConversationHandler.END
            
            # 成功
            text = (
                f"✅ <b>购买成功！</b>\n\n"
                f"📦 订单号：<code>{order.order_id}</code>\n"
                f"📍 地址：<code>{receive_address}</code>\n"
            )
            
            if energy_type == EnergyOrderType.HOURLY:
                text += (
                    f"\n⚡ 能量已发送到您的地址\n"
                    f"⏰ 有效期：1小时\n\n"
                    f"💡 提示：请在1小时内使用完毕"
                )
            elif energy_type == EnergyOrderType.PACKAGE:
                text += (
                    f"\n📦 笔数套餐已激活\n\n"
                    f"💡 提示：\n"
                    f"• 每天至少使用一次\n"
                    f"• 有U扣1笔，无U扣2笔"
                )
            
            await query.edit_message_text(
                text=text,
                parse_mode="HTML"
            )
            
            logger.info(f"能量订单完成: {order.order_id}, 用户: {user_id}")
            
        except Exception as e:
            logger.error(f"能量订单处理失败: {e}")
            await query.edit_message_text(
                text=f"❌ <b>订单处理失败</b>\n\n{str(e)}\n\n请联系客服处理",
                parse_mode="HTML"
            )
        
        return ConversationHandler.END
    
    async def input_usdt_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """输入USDT金额（笔数套餐）"""
        message = update.message
        
        try:
            amount = float(message.text.strip())
            
            if amount < 5:
                await message.reply_text(
                    "❌ 最低充值金额为 5 USDT，请重新输入："
                )
                return STATE_INPUT_USDT
            
            context.user_data["usdt_amount"] = amount
            
            # 跳转到输入地址
            estimated_count = int(amount * 7 / 3.6)
            
            text = (
                f"📍 <b>接收地址</b>\n\n"
                f"充值金额：{amount} USDT\n"
                f"预计笔数：约{estimated_count}笔\n\n"
                f"请输入接收能量的波场地址：\n\n"
                f"⚠️ 注意：\n"
                f"• 必须是有效的波场地址（T开头）\n"
                f"• 笔数将绑定到此地址\n"
                f"• 弹性扣费：有U扣1笔，无U扣2笔"
            )
            
            await message.reply_text(text, parse_mode="HTML")
            
            return STATE_INPUT_ADDRESS
            
        except ValueError:
            await message.reply_text(
                "❌ 请输入有效的金额（数字）："
            )
            return STATE_INPUT_USDT
    
    async def _cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消兑换 - 支持message和callback_query"""
        context.user_data.clear()
        
        if update.callback_query:
            await update.callback_query.answer("已取消")
            try:
                await update.callback_query.edit_message_text("❌ 已取消能量兑换")
            except:
                await update.effective_message.reply_text("❌ 已取消能量兑换")
        elif update.message:
            await update.message.reply_text("❌ 已取消能量兑换")
        else:
            if update.effective_message:
                await update.effective_message.reply_text("❌ 已取消能量兑换")
        
        return ConversationHandler.END
    
    def get_conversation_handler(self) -> ConversationHandler:
        """获取对话处理器"""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.start_energy, pattern="^energy_exchange$")
            ],
            states={
                STATE_SELECT_TYPE: [
                    CallbackQueryHandler(self.select_type, pattern="^energy_type_")
                ],
                STATE_SELECT_PACKAGE: [
                    CallbackQueryHandler(self.input_count, pattern="^package_")
                ],
                STATE_INPUT_COUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_address)
                ],
                STATE_INPUT_USDT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_usdt_amount)
                ],
                STATE_INPUT_ADDRESS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_order)
                ],
                STATE_CONFIRM: [
                    CallbackQueryHandler(self.process_order, pattern="^energy_confirm_")
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.start_energy, pattern="^energy_start$")
            ],
        )
