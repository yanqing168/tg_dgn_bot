"""
能量兑换模块主处理器 - 标准化版本
"""

import logging
import uuid
from typing import List
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    BaseHandler,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from src.core.base import BaseModule
from src.core.formatter import MessageFormatter
from src.core.state_manager import ModuleStateManager
from src.common.conversation_wrapper import SafeConversationHandler
from src.common.navigation_manager import NavigationManager

from .messages import EnergyMessages
from .states import *
from .keyboards import EnergyKeyboards

# 从 legacy 导入业务逻辑类
from src.legacy.energy.models import EnergyPackage, EnergyOrderType
from src.legacy.address_query.validator import AddressValidator
from src.config import settings
from src.database import SessionLocal, EnergyOrder as DBEnergyOrder
from src.common.settings_service import get_order_timeout_minutes

logger = logging.getLogger(__name__)


class EnergyModule(BaseModule):
    """标准化的能量兑换模块"""
    
    def __init__(self):
        """初始化能量模块"""
        self.formatter = MessageFormatter()
        self.state_manager = ModuleStateManager()
        self.validator = AddressValidator()
    
    @property
    def module_name(self) -> str:
        """模块名称"""
        return "energy"
    
    def get_handlers(self) -> List[BaseHandler]:
        """
        获取模块处理器
        
        Returns:
            包含ConversationHandler的列表
        """
        conv_handler = SafeConversationHandler.create(
            entry_points=[
                CommandHandler("energy", self.start_energy),
                CallbackQueryHandler(self.start_energy, pattern="^energy$"),
                MessageHandler(filters.Regex("^⚡ 能量兑换$"), self.start_energy),
            ],
            states={
                STATE_SELECT_TYPE: [
                    CallbackQueryHandler(self.select_type, pattern="^energy_type_"),
                ],
                STATE_SELECT_PACKAGE: [
                    CallbackQueryHandler(self.select_package_callback, pattern="^energy_pkg_"),
                    CallbackQueryHandler(self.back_to_type, pattern="^energy_back$"),
                ],
                STATE_INPUT_ADDRESS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_address),
                ],
                STATE_INPUT_COUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_count),
                ],
                STATE_INPUT_USDT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_usdt_amount),
                ],
                STATE_SHOW_PAYMENT: [
                    CallbackQueryHandler(self.payment_done, pattern="^energy_payment_done$"),
                ],
                STATE_INPUT_TX_HASH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_tx_hash_input),
                    CallbackQueryHandler(self.skip_tx_hash, pattern="^energy_skip_hash$"),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(self.cancel, pattern="^energy_cancel$"),
                CallbackQueryHandler(self.cancel, pattern="^back_to_main$"),
                CommandHandler("cancel", self.cancel),
            ],
            name="energy_conversation",
            allow_reentry=True,
        )
        
        return [conv_handler]
    
    def _get_timeout_minutes(self, context: ContextTypes.DEFAULT_TYPE) -> int:
        """获取订单超时时间"""
        state = self.state_manager.get_state(context, self.module_name)
        if "timeout_minutes" not in state:
            state["timeout_minutes"] = get_order_timeout_minutes()
        return state["timeout_minutes"]
    
    async def start_energy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        开始能量兑换流程
        兼容 CallbackQuery 和 Message 两种入口
        """
        # 初始化状态
        self.state_manager.init_state(context, self.module_name)
        
        # 兼容不同入口
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            send_method = query.edit_message_text
        else:
            send_method = update.message.reply_text
        
        # 获取超时时间
        timeout_minutes = self._get_timeout_minutes(context)
        
        # 格式化消息
        text = EnergyMessages.MAIN_MENU.format(timeout_minutes=timeout_minutes)
        
        # 发送消息
        await send_method(
            text=text,
            reply_markup=EnergyKeyboards.main_menu(),
            parse_mode="HTML"
        )
        
        return STATE_SELECT_TYPE
    
    async def select_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """选择能量类型"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # 直接使用context.user_data保存状态
        if data == "energy_type_hourly":
            # 时长能量（闪租）
            context.user_data["energy_type"] = EnergyOrderType.HOURLY.value
            return await self._show_hourly_packages(query, context)
            
        elif data == "energy_type_package":
            # 笔数套餐
            context.user_data["energy_type"] = EnergyOrderType.PACKAGE.value
            return await self._show_package_input(query, context)
            
        elif data == "energy_type_flash":
            # 闪兑
            context.user_data["energy_type"] = EnergyOrderType.FLASH.value
            return await self._show_flash_input(query, context)
        
        return STATE_SELECT_TYPE
    
    async def _show_hourly_packages(self, query, context: ContextTypes.DEFAULT_TYPE) -> int:
        """显示时长能量套餐"""
        text = EnergyMessages.HOURLY_PACKAGES
        
        await query.edit_message_text(
            text=text,
            reply_markup=EnergyKeyboards.hourly_packages(),
            parse_mode="HTML"
        )
        
        return STATE_SELECT_PACKAGE
    
    async def _show_package_input(self, query, context: ContextTypes.DEFAULT_TYPE) -> int:
        """显示笔数套餐输入"""
        text = EnergyMessages.PACKAGE_INFO
        
        await query.edit_message_text(
            text=text,
            reply_markup=EnergyKeyboards.back_and_cancel(),
            parse_mode="HTML"
        )
        
        return STATE_INPUT_USDT
    
    async def _show_flash_input(self, query, context: ContextTypes.DEFAULT_TYPE) -> int:
        """显示闪兑输入"""
        text = EnergyMessages.FLASH_EXCHANGE
        
        await query.edit_message_text(
            text=text,
            reply_markup=EnergyKeyboards.back_and_cancel(),
            parse_mode="HTML"
        )
        
        return STATE_INPUT_USDT
    
    async def select_package_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """选择时长能量套餐"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id if query.from_user else 'unknown'
        data = query.data
        logger.info(f"用户 {user_id} 选择套餐: {data}")
        
        # 解析套餐 - 直接保存到context.user_data
        if data == "energy_pkg_65k":
            context.user_data["energy_amount"] = 65000
            context.user_data["price_trx"] = 3
        elif data == "energy_pkg_131k":
            context.user_data["energy_amount"] = 131000
            context.user_data["price_trx"] = 6
        else:
            return STATE_SELECT_PACKAGE
        
        # 请求输入地址
        text = EnergyMessages.INPUT_ADDRESS
        
        await query.edit_message_text(
            text=text,
            reply_markup=EnergyKeyboards.back_and_cancel(),
            parse_mode="HTML"
        )
        
        return STATE_INPUT_ADDRESS
    
    async def back_to_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """返回类型选择"""
        query = update.callback_query
        await query.answer()
        
        # 清除当前选择 - 直接从context.user_data清除
        context.user_data.pop("energy_type", None)
        context.user_data.pop("energy_amount", None)
        context.user_data.pop("price_trx", None)
        
        # 显示主菜单
        timeout_minutes = self._get_timeout_minutes(context)
        text = EnergyMessages.MAIN_MENU.format(timeout_minutes=timeout_minutes)
        
        await query.edit_message_text(
            text=text,
            reply_markup=EnergyKeyboards.main_menu(),
            parse_mode="HTML"
        )
        
        return STATE_SELECT_TYPE
    
    async def input_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """输入接收地址"""
        message = update.message
        address = message.text.strip()
        user_id = message.from_user.id if message.from_user else 'unknown'
        
        logger.info(f"用户 {user_id} 输入地址: {address}")
        
        # 验证地址
        is_valid, error_msg = self.validator.validate(address)
        if not is_valid:
            logger.warning(f"无效地址: {address}, 错误: {error_msg}")
            error_text = EnergyMessages.INVALID_ADDRESS
            await message.reply_text(
                text=error_text,
                parse_mode="HTML"
            )
            return STATE_INPUT_ADDRESS
        
        # 保存地址 - 直接保存到context.user_data
        context.user_data["receive_address"] = address
        logger.info(f"地址验证通过，准备显示支付信息")
        
        # 显示支付信息
        result = await self._show_payment_info(message, context)
        logger.info(f"_show_payment_info 返回状态: {result}")
        return result
    
    async def input_count(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """输入购买笔数（笔数套餐）"""
        message = update.message
        
        try:
            count = int(message.text.strip())
            if count < 1:
                raise ValueError("笔数必须大于0")
        except ValueError as e:
            error_text = EnergyMessages.INVALID_AMOUNT.format(
                error_message=self.formatter.escape_html(str(e))
            )
            await message.reply_text(text=error_text, parse_mode="HTML")
            return STATE_INPUT_COUNT
        
        # 保存笔数
        state = self.state_manager.get_state(context, self.module_name)
        state["count"] = count
        
        # 请求输入地址
        text = EnergyMessages.INPUT_ADDRESS
        await message.reply_text(text=text, parse_mode="HTML")
        
        return STATE_INPUT_ADDRESS
    
    async def input_usdt_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """输入USDT金额（笔数套餐/闪兑）"""
        message = update.message
        energy_type = context.user_data.get("energy_type")
        
        try:
            amount = float(message.text.strip())
            
            # 验证金额
            if energy_type == EnergyOrderType.PACKAGE.value and amount < 5:
                raise ValueError("笔数套餐最低 5 USDT")
            elif energy_type == EnergyOrderType.FLASH.value and amount < 1:
                raise ValueError("闪兑最低 1 USDT")
            elif amount <= 0:
                raise ValueError("金额必须大于0")
                
        except ValueError as e:
            error_text = EnergyMessages.INVALID_AMOUNT.format(
                error_message=self.formatter.escape_html(str(e))
            )
            await message.reply_text(text=error_text, parse_mode="HTML")
            return STATE_INPUT_USDT
        
        # 保存金额 - 直接保存到context.user_data
        context.user_data["usdt_amount"] = amount
        
        # 请求输入地址
        text = EnergyMessages.INPUT_ADDRESS
        await message.reply_text(text=text, parse_mode="HTML")
        
        return STATE_INPUT_ADDRESS
    
    async def _show_payment_info(self, message, context: ContextTypes.DEFAULT_TYPE) -> int:
        """显示支付信息"""
        energy_type = context.user_data.get("energy_type")
        receive_address = context.user_data.get("receive_address")
        
        # 创建订单ID
        order_id = str(uuid.uuid4())
        context.user_data["order_id"] = order_id
        
        # 保存user_id
        if message.from_user:
            context.user_data["user_id"] = message.from_user.id
        
        # 获取超时时间
        timeout_minutes = self._get_timeout_minutes(context)
        
        # 根据类型显示不同的支付信息
        if energy_type == EnergyOrderType.HOURLY.value:
            # 时长能量 - TRX支付
            energy_amount = context.user_data.get("energy_amount")
            price_trx = context.user_data.get("price_trx")
            payment_address = settings.trx_receive_addr if hasattr(settings, 'trx_receive_addr') else "TPaymentAddress123"
            
            text = EnergyMessages.PAYMENT_INFO_HOURLY.format(
                energy_amount=energy_amount,
                price=price_trx,
                receive_address=receive_address,
                payment_address=payment_address,
                timeout_minutes=timeout_minutes,
                order_id=order_id
            )
        else:
            # 笔数套餐/闪兑 - USDT支付
            usdt_amount = context.user_data.get("usdt_amount")
            order_type_name = "笔数套餐" if energy_type == EnergyOrderType.PACKAGE.value else "闪兑"
            payment_address = settings.usdt_trc20_receive_addr
            
            text = EnergyMessages.PAYMENT_INFO_USDT.format(
                order_type=order_type_name,
                amount=usdt_amount,
                receive_address=receive_address,
                payment_address=payment_address,
                timeout_minutes=timeout_minutes,
                order_id=order_id
            )
        
        # 保存订单到数据库（简化版本）
        try:
            await self._create_order(context.user_data, order_id, timeout_minutes)
            logger.info(f"能量订单创建成功: {order_id}")
        except Exception as e:
            logger.error(f"创建订单失败，但继续流程: {e}", exc_info=True)
            # 即使订单创建失败，也继续显示支付信息
        
        # 发送支付信息
        logger.info(f"发送支付信息给用户: {message.from_user.id if message.from_user else 'unknown'}")
        await message.reply_text(
            text=text,
            reply_markup=EnergyKeyboards.payment_done(),
            parse_mode="HTML"
        )
        
        logger.info(f"返回状态: STATE_SHOW_PAYMENT ({STATE_SHOW_PAYMENT})")
        return STATE_SHOW_PAYMENT
    
    async def payment_done(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """用户确认已转账"""
        query = update.callback_query
        await query.answer()
        
        order_id = context.user_data.get("order_id")
        
        # 请求输入交易哈希
        text = EnergyMessages.WAITING_TX_HASH.format(order_id=order_id)
        
        await query.edit_message_text(
            text=text,
            reply_markup=EnergyKeyboards.skip_tx_hash(),
            parse_mode="HTML"
        )
        
        return STATE_INPUT_TX_HASH
    
    async def handle_tx_hash_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """接收用户输入的交易哈希"""
        message = update.message
        tx_hash = message.text.strip()
        
        order_id = context.user_data.get("order_id")
        
        # 保存交易哈希
        await self._save_tx_hash(order_id, tx_hash)
        
        # 显示确认消息
        text = EnergyMessages.ORDER_SUBMITTED.format(
            order_id=order_id,
            tx_hash=tx_hash
        )
        
        await message.reply_text(text=text, parse_mode="HTML")
        
        # 清理状态
        self.state_manager.clear_state(context, self.module_name)
        
        return ConversationHandler.END
    
    async def skip_tx_hash(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """跳过交易哈希输入"""
        query = update.callback_query
        await query.answer()
        
        order_id = context.user_data.get("order_id")
        
        # 显示确认消息
        text = EnergyMessages.ORDER_SKIP_HASH.format(order_id=order_id)
        
        await query.edit_message_text(text=text, parse_mode="HTML")
        
        # 清理状态
        self.state_manager.clear_state(context, self.module_name)
        
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消操作"""
        query = update.callback_query
        if query:
            await query.answer()
        
        # 使用统一的导航管理器（会自动清理状态）
        return await NavigationManager.cleanup_and_show_main_menu(update, context)
    
    async def _create_order(self, state: dict, order_id: str, timeout_minutes: int):
        """创建订单（简化版本）"""
        try:
            db = SessionLocal()
            
            energy_type = state.get("energy_type")
            receive_address = state.get("receive_address")
            user_id = state.get("user_id", 0)  # 获取user_id
            
            # 创建订单记录
            db_order = DBEnergyOrder(
                order_id=order_id,
                user_id=user_id,
                order_type=energy_type,  # 使用order_type而不是energy_type
                receive_address=receive_address,
                status="pending",
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=timeout_minutes)
            )
            
            # 根据类型设置不同字段
            if energy_type == EnergyOrderType.HOURLY.value:
                db_order.energy_amount = state.get("energy_amount")
                db_order.price_trx = state.get("price_trx")
            else:
                db_order.usdt_amount = state.get("usdt_amount")
            
            db.add(db_order)
            db.commit()
            
            logger.info(f"创建能量订单: {order_id}")
            
        except Exception as e:
            logger.error(f"创建订单失败: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()
    
    async def _save_tx_hash(self, order_id: str, tx_hash: str):
        """保存交易哈希"""
        try:
            db = SessionLocal()
            
            db_order = db.query(DBEnergyOrder).filter_by(order_id=order_id).first()
            if db_order:
                db_order.tx_hash = tx_hash
                db_order.updated_at = datetime.now()
                db.commit()
                logger.info(f"保存交易哈希: {order_id} -> {tx_hash}")
            
        except Exception as e:
            logger.error(f"保存交易哈希失败: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()
