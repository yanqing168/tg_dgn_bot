"""
地址查询 Telegram Bot 处理器
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from datetime import datetime, timedelta
from typing import Optional
import logging
import httpx

from ..database import SessionLocal, AddressQueryLog
from ..config import settings
from src.common.settings_service import get_address_cooldown_minutes
from src.common.decorators import error_handler, log_action
# 从 legacy 导入业务逻辑类
from ..legacy.address_query.validator import AddressValidator
from ..legacy.address_query.explorer import explorer_links

logger = logging.getLogger(__name__)

# 对话状态
AWAITING_ADDRESS = 1


class AddressQueryHandler:
    """地址查询处理器"""
    
    @staticmethod
    @error_handler
    @log_action("地址查询_开始")
    async def start_query_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始地址查询对话（ConversationHandler入口）"""
        query = update.callback_query
        if query:
            await query.answer()
        
        user_id = update.effective_user.id
        
        # 检查限频
        can_query, remaining_minutes = AddressQueryHandler._check_rate_limit(user_id)
        cooldown_minutes = get_address_cooldown_minutes()
        
        if not can_query:
            text = (
                f"⏰ <b>查询限制</b>\n\n"
                f"您的查询过于频繁，请在 <b>{remaining_minutes}</b> 分钟后再试。\n\n"
                f"💡 免费功能，每用户 {cooldown_minutes} 分钟可查询 1 次"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if query:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            return ConversationHandler.END
        
        # 提示输入地址
        text = (
            "🔍 <b>地址查询</b>\n\n"
            "请发送要查询的波场(TRON)地址：\n\n"
            "• 地址以 <code>T</code> 开头\n"
            "• 长度为 34 位字符\n"
            "• 支持 Base58 字符集\n\n"
            "示例: <code>TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH</code>"
        )
        
        keyboard = [[InlineKeyboardButton("❌ 取消", callback_data="cancel_query")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
        elif update.message:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
        
        # 返回等待地址输入的状态
        return AWAITING_ADDRESS
    
    @staticmethod
    async def query_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理地址查询按钮点击（保留用于兼容性，实际调用start_query_conversation）"""
        return await AddressQueryHandler.start_query_conversation(update, context)
    
    @staticmethod
    @error_handler
    @log_action("地址查询_处理输入")
    async def handle_address_input_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """在对话中处理用户输入的地址（ConversationHandler版本）"""
        try:
            # 清理地址：移除所有空白字符（包括不可见字符）
            address = ''.join(update.message.text.split())
            user_id = update.effective_user.id
            
            logger.info(f"用户 {user_id} 查询地址: {address}")
            
            # 验证地址格式
            is_valid, error_msg = AddressValidator.validate(address)
            
            if not is_valid:
                text = f"❌ <b>地址格式错误</b>\n\n{error_msg}\n\n请重新发送正确的地址。"
                keyboard = [[InlineKeyboardButton("❌ 取消", callback_data="cancel_query")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
                return AWAITING_ADDRESS  # 继续等待输入
            
            # 再次检查限频（防止绕过）
            can_query, remaining_minutes = AddressQueryHandler._check_rate_limit(user_id)
            cooldown_minutes = get_address_cooldown_minutes()
            if not can_query:
                text = (
                    f"⏰ <b>查询限制</b>\n\n"
                    f"您的查询过于频繁，请在 <b>{remaining_minutes}</b> 分钟后再次尝试。\n\n"
                    f"💡 每 {cooldown_minutes} 分钟可查询 1 次"
                )
                keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
                return ConversationHandler.END
            
            # 记录查询
            AddressQueryHandler._record_query(user_id)
            
            # 显示查询中提示
            processing_msg = await update.message.reply_text("🔄 正在查询地址信息...")
            
            # 获取地址信息
            address_info = await AddressQueryHandler._fetch_address_info(address)
            
            # 生成浏览器链接
            links = explorer_links(address)
            
            # 构建响应消息
            text = f"📍 <b>地址信息</b>\n\n"
            text += f"地址: <code>{address}</code>\n\n"
            
            if address_info:
                text += f"💰 TRX 余额: <b>{address_info.get('trx_balance', '0')} TRX</b>\n"
                text += f"🪙 USDT 余额: <b>{address_info.get('usdt_balance', '0')} USDT</b>\n\n"
                
                # 最近交易
                txs = address_info.get('recent_txs', [])
                if txs:
                    text += "📊 <b>最近 5 笔交易:</b>\n\n"
                    for idx, tx in enumerate(txs[:5], 1):
                        direction = tx.get('direction', '?')
                        amount = tx.get('amount', '0')
                        token = tx.get('token', 'TRX')
                        tx_hash = tx.get('hash', '')
                        timestamp = tx.get('time', '')
                        
                        text += f"{idx}. {direction} {amount} {token}\n"
                        text += f"   哈希: <code>{tx_hash}...</code>\n"
                        text += f"   时间: {timestamp}\n\n"
                else:
                    text += "📊 <i>暂无最近交易记录</i>\n\n"
            else:
                text += "ℹ️ <i>API 暂时不可用，无法获取详细信息</i>\n\n"
                text += "地址格式正确，您可以通过下方链接查看详情。\n\n"
            
            text += "如需再次查询，可稍后重新发送地址。"
            
            # 添加深链接按钮
            keyboard = [
                [
                    InlineKeyboardButton("🔗 链上查询详情", url=links["overview"]),
                    InlineKeyboardButton("🔍 查询转账记录", url=links["txs"])
                ],
                [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # 删除"查询中"提示
            try:
                await processing_msg.delete()
            except Exception:
                pass  # 忽略删除失败
            
            # 发送结果
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            
            logger.info(f"用户 {user_id} 查询地址成功: {address}")
            
            # 结束对话
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"处理地址输入时出错: {e}", exc_info=True)
            # 发送错误提示给用户
            error_text = (
                "❌ <b>查询失败</b>\n\n"
                "系统处理您的请求时出现错误，请稍后重试。\n\n"
                "如果问题持续存在，请联系客服。"
            )
            keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await update.message.reply_text(error_text, parse_mode="HTML", reply_markup=reply_markup)
            except Exception:
                pass
            
            # 错误时也结束对话
            return ConversationHandler.END
    
    @staticmethod
    async def handle_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理用户输入的地址（保留用于向后兼容，现已不使用）"""
        # 这个方法保留是为了向后兼容，但在ConversationHandler模式下不会被调用
        # 如果被误调用，提示用户
        await update.message.reply_text(
            "⚠️ 请先点击「🔍 地址查询」按钮开始查询流程。",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
            )
        )
    
    @staticmethod
    @log_action("地址查询_取消")
    async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消地址查询对话"""
        query = update.callback_query
        if query:
            await query.answer("❌ 已取消地址查询")
            await query.edit_message_text(
                "❌ 地址查询已取消。",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
                )
            )
        else:
            await update.message.reply_text(
                "❌ 地址查询已取消。",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
                )
            )
        return ConversationHandler.END
    
    @staticmethod
    def _check_rate_limit(user_id: int) -> tuple[bool, int]:
        """检查用户是否在限频期内，返回 (是否允许, 剩余分钟数)。"""
        db = SessionLocal()
        try:
            log = db.query(AddressQueryLog).filter_by(user_id=user_id).first()
            cooldown_minutes = get_address_cooldown_minutes()

            if not log:
                return True, 0

            now = datetime.now()
            limit_delta = timedelta(minutes=cooldown_minutes)
            time_passed = now - log.last_query_at

            if time_passed >= limit_delta:
                return True, 0

            remaining_seconds = (limit_delta - time_passed).total_seconds()
            remaining_minutes = max(1, int((remaining_seconds + 59) // 60))
            return False, remaining_minutes
        finally:
            db.close()

    @staticmethod
    def _record_query(user_id: int) -> None:
        """记录一次查询时间（用于限频统计）。"""
        db = SessionLocal()
        try:
            log = db.query(AddressQueryLog).filter_by(user_id=user_id).first()
            now = datetime.now()

            if not log:
                log = AddressQueryLog(
                    user_id=user_id,
                    last_query_at=now,
                    query_count=1,
                )
                db.add(log)
            else:
                log.last_query_at = now
                log.query_count = (log.query_count or 0) + 1

            db.commit()
        finally:
            db.close()

    @staticmethod
    async def _fetch_address_info(address: str) -> Optional[dict]:
        """
        获取地址信息（从 TronScan API）

        Args:
            address: 波场地址

        Returns:
            地址信息字典，失败返回 None
        """
        if not settings.tron_api_key:
            logger.info("TRON API Key 未配置，跳过数据获取")
            return None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                headers = {"TRON-PRO-API-KEY": settings.tron_api_key}

                account_url = "https://apilist.tronscanapi.com/api/accountv2"
                params = {"address": address}

                response = await client.get(account_url, headers=headers, params=params)

                if response.status_code != 200:
                    logger.warning("TronScan API 返回错误: %s - %s", response.status_code, response.text)
                    return None

                data = response.json()
                result = {}

                balance_raw = data.get("balance", 0)
                try:
                    balance_sun = int(balance_raw)
                except (TypeError, ValueError):
                    logger.warning("TronScan balance 字段无法解析: %s", balance_raw)
                    balance_sun = 0
                result["trx_balance"] = f"{balance_sun / 1_000_000:.6f}"

                usdt_balance = 0
                trc20_tokens = data.get("trc20token_balances", [])
                for token in trc20_tokens:
                    if token.get("tokenAbbr") == "USDT" or token.get("tokenName") == "Tether USD":
                        try:
                            balance_val = int(token.get("balance", 0))
                        except (TypeError, ValueError):
                            balance_val = 0
                        usdt_balance = balance_val / 1_000_000
                        break

                result["usdt_balance"] = f"{usdt_balance:.2f}"

                tx_url = "https://apilist.tronscanapi.com/api/transaction"
                tx_params = {"address": address, "limit": 5, "start": 0}

                tx_response = await client.get(tx_url, headers=headers, params=tx_params)

                recent_txs = []
                if tx_response.status_code == 200:
                    tx_data = tx_response.json()
                    transactions = tx_data.get("data", [])

                    for tx in transactions[:5]:
                        owner_address = tx.get("ownerAddress", "")
                        to_address = tx.get("toAddress", "")

                        if to_address == address:
                            direction = "📥 转入"
                        elif owner_address == address:
                            direction = "📤 转出"
                        else:
                            direction = "🔄"

                        try:
                            amount_val = int(tx.get("amount", 0))
                        except (TypeError, ValueError):
                            amount_val = 0
                        amount = amount_val / 1_000_000
                        token = tx.get("tokenInfo", {}).get("tokenAbbr", "TRX")

                        if tx.get("contractType") == 31:
                            token_info = tx.get("tokenInfo", {})
                            if token_info:
                                decimals = int(token_info.get("tokenDecimal", 6))
                                try:
                                    token_amt_raw = int(tx.get("amount", 0))
                                except (TypeError, ValueError):
                                    token_amt_raw = 0
                                amount = token_amt_raw / (10 ** decimals)
                                token = token_info.get("tokenAbbr", "TRC20")

                        timestamp = tx.get("timestamp", 0)
                        time_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M")

                        recent_txs.append(
                            {
                                "direction": direction,
                                "amount": f"{amount:.2f}" if amount > 0.01 else f"{amount:.6f}",
                                "token": token,
                                "hash": tx.get("hash", "")[:10],
                                "time": time_str,
                            }
                        )
                else:
                    logger.warning("获取交易记录失败: %s", tx_response.status_code)

                result["recent_txs"] = recent_txs
                return result

        except httpx.TimeoutException:
            logger.error("TronScan API 请求超时")
            return None
        except Exception as e:
            logger.error("获取地址信息失败: %s", e)
            return None
    
    @staticmethod
    async def cancel_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """取消查询（保留用于兼容）"""
        return await AddressQueryHandler.cancel_conversation(update, context)
    
    @staticmethod
    def get_conversation_handler() -> ConversationHandler:
        """获取地址查询ConversationHandler"""
        return ConversationHandler(
            entry_points=[
                # Inline按钮入口
                CallbackQueryHandler(
                    AddressQueryHandler.start_query_conversation,
                    pattern=r"^menu_address_query$"
                ),
                # Reply按钮入口
                MessageHandler(
                    filters.Regex(r"^🔍 地址查询$"),
                    AddressQueryHandler.start_query_conversation
                )
            ],
            states={
                AWAITING_ADDRESS: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        AddressQueryHandler.handle_address_input_conversation
                    )
                ]
            },
            fallbacks=[
                CallbackQueryHandler(
                    AddressQueryHandler.cancel_conversation,
                    pattern=r"^(cancel_query|back_to_main)$"
                ),
                CommandHandler("cancel", AddressQueryHandler.cancel_conversation),
                # 当用户点击其他功能按钮时，自动结束当前对话
                CallbackQueryHandler(
                    AddressQueryHandler.cancel_conversation,
                    pattern=r"^(menu_premium|menu_profile|menu_energy|menu_clone|menu_support)$"
                ),
            ],
            name="address_query",
            persistent=False,
            allow_reentry=True,
            per_chat=True,
            per_user=True,
            per_message=False,
        )
