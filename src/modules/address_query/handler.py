"""
地址查询模块主处理器 - 标准化版本
"""

import logging
from typing import List, Optional, Dict
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

from .messages import AddressQueryMessages
from .states import *
from .keyboards import AddressQueryKeyboards

# 从 legacy 导入业务逻辑类
from src.legacy.address_query.validator import AddressValidator
from src.legacy.address_query.explorer import explorer_links
from src.database import SessionLocal, AddressQueryLog
from src.common.settings_service import get_address_cooldown_minutes

logger = logging.getLogger(__name__)


class AddressQueryModule(BaseModule):
    """标准化的地址查询模块"""
    
    def __init__(self):
        """初始化地址查询模块"""
        self.formatter = MessageFormatter()
        self.state_manager = ModuleStateManager()
        self.validator = AddressValidator()
    
    @property
    def module_name(self) -> str:
        """模块名称"""
        return "address_query"
    
    def get_handlers(self) -> List[BaseHandler]:
        """
        获取模块处理器
        
        Returns:
            包含ConversationHandler的列表
        """
        conv_handler = SafeConversationHandler.create(
            entry_points=[
                CommandHandler("query", self.start_query),
                CallbackQueryHandler(self.start_query, pattern="^address_query$"),
                MessageHandler(filters.Regex("^🔍 地址查询$"), self.start_query),
            ],
            states={
                AWAITING_ADDRESS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_address_input),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(self.cancel, pattern="^addrq_cancel$"),
                CallbackQueryHandler(self.cancel, pattern="^addrq_back_to_main$"),
                CommandHandler("cancel", self.cancel),
            ],
            name="address_query_conversation",
            allow_reentry=True,
        )
        
        return [conv_handler]
    
    async def start_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        开始地址查询
        兼容 CallbackQuery 和 Message 两种入口
        """
        # 初始化状态
        self.state_manager.init_state(context, self.module_name)
        
        user_id = update.effective_user.id
        
        # 检查限频
        can_query, remaining_minutes = self._check_rate_limit(user_id)
        cooldown_minutes = get_address_cooldown_minutes()
        
        if not can_query:
            text = AddressQueryMessages.RATE_LIMIT.format(
                remaining_minutes=remaining_minutes,
                cooldown_minutes=cooldown_minutes
            )
            
            keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="addrq_back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # 兼容不同入口
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            
            return ConversationHandler.END
        
        # 提示输入地址
        text = AddressQueryMessages.START_QUERY
        
        keyboard = [[InlineKeyboardButton("❌ 取消", callback_data="addrq_cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # 兼容不同入口
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        
        return AWAITING_ADDRESS
    
    async def handle_address_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理用户输入的地址"""
        try:
            # 清理地址：移除所有空白字符
            address = ''.join(update.message.text.split())
            user_id = update.effective_user.id
            
            logger.info(f"用户 {user_id} 查询地址: {address}")
            
            # 验证地址格式
            is_valid, error_msg = self.validator.validate(address)
            
            if not is_valid:
                text = AddressQueryMessages.INVALID_ADDRESS.format(
                    error_msg=self.formatter.escape_html(error_msg)
                )
                keyboard = [[InlineKeyboardButton("❌ 取消", callback_data="addrq_cancel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                return AWAITING_ADDRESS  # 继续等待输入
            
            # 再次检查限频（防止绕过）
            can_query, remaining_minutes = self._check_rate_limit(user_id)
            cooldown_minutes = get_address_cooldown_minutes()
            
            if not can_query:
                text = AddressQueryMessages.RATE_LIMIT.format(
                    remaining_minutes=remaining_minutes,
                    cooldown_minutes=cooldown_minutes
                )
                keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="addrq_back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                return ConversationHandler.END
            
            # 记录查询
            self._record_query(user_id)
            
            # 显示查询中提示
            processing_msg = await update.message.reply_text(AddressQueryMessages.PROCESSING)
            
            # 获取地址信息
            address_info = await self._fetch_address_info(address)
            
            # 生成浏览器链接
            links = explorer_links(address)
            
            # 构建响应消息
            if address_info:
                # 有API数据
                trx_balance = address_info.get('trx_balance', '0')
                usdt_balance = address_info.get('usdt_balance', '0')
                
                # 处理最近交易
                txs = address_info.get('recent_txs', [])
                if txs:
                    transaction_list = ""
                    for idx, tx in enumerate(txs[:5], 1):
                        direction = tx.get('direction', '?')
                        amount = tx.get('amount', '0')
                        token = tx.get('token', 'TRX')
                        tx_hash = tx.get('hash', '')[:10]  # 只显示前10位
                        timestamp = tx.get('time', '')
                        
                        transaction_list += f"{idx}. {direction} {amount} {token}\n"
                        transaction_list += f"   哈希: <code>{tx_hash}...</code>\n"
                        transaction_list += f"   时间: {timestamp}\n\n"
                    
                    transactions_info = AddressQueryMessages.RECENT_TRANSACTIONS.format(
                        transaction_list=transaction_list
                    )
                else:
                    transactions_info = AddressQueryMessages.NO_TRANSACTIONS
                
                text = AddressQueryMessages.QUERY_RESULT.format(
                    address=address,
                    trx_balance=trx_balance,
                    usdt_balance=usdt_balance,
                    transactions_info=transactions_info
                )
            else:
                # 无API数据
                text = AddressQueryMessages.QUERY_RESULT_NO_API.format(address=address)
            
            # 添加深链接按钮
            keyboard = [
                [
                    InlineKeyboardButton("🔗 链上查询详情", url=links["overview"]),
                    InlineKeyboardButton("🔍 查询转账记录", url=links["txs"])
                ],
                [InlineKeyboardButton("🔙 返回主菜单", callback_data="addrq_back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # 删除"查询中"提示
            try:
                await processing_msg.delete()
            except Exception:
                pass  # 忽略删除失败
            
            # 发送结果
            await update.message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"用户 {user_id} 查询地址成功: {address}")
            
            # 清理状态
            self.state_manager.clear_state(context, self.module_name)
            
            # 结束对话
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"处理地址输入时出错: {e}", exc_info=True)
            
            # 发送错误提示
            text = AddressQueryMessages.QUERY_ERROR
            keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="addrq_back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await update.message.reply_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            except Exception:
                pass
            
            return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消操作"""
        query = update.callback_query
        if query:
            await query.answer()
        
        # 使用统一的导航管理器（会自动清理状态）
        return await NavigationManager.cleanup_and_show_main_menu(update, context)
    
    def _check_rate_limit(self, user_id: int) -> tuple[bool, int]:
        """
        检查用户查询限频
        
        Args:
            user_id: 用户ID
            
        Returns:
            (是否可以查询, 剩余分钟数)
        """
        try:
            db = SessionLocal()
            cooldown_minutes = get_address_cooldown_minutes()
            
            # 查询最近一次查询记录
            last_query = db.query(AddressQueryLog).filter_by(
                user_id=user_id
            ).order_by(AddressQueryLog.last_query_at.desc()).first()
            
            if last_query:
                time_since_last = datetime.now() - last_query.last_query_at
                if time_since_last < timedelta(minutes=cooldown_minutes):
                    remaining = cooldown_minutes - int(time_since_last.total_seconds() / 60)
                    return False, max(1, remaining)
            
            return True, 0
            
        except Exception as e:
            logger.error(f"检查限频失败: {e}", exc_info=True)
            return True, 0  # 出错时允许查询
        finally:
            db.close()
    
    def _record_query(self, user_id: int):
        """记录查询"""
        try:
            db = SessionLocal()
            
            log = AddressQueryLog(
                user_id=user_id,
                last_query_at=datetime.now()
            )
            db.add(log)
            db.commit()
            
        except Exception as e:
            logger.error(f"记录查询失败: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()
    
    async def _fetch_address_info(self, address: str) -> Optional[Dict]:
        """
        获取地址信息（使用TronGrid API）
        
        Args:
            address: TRON地址
            
        Returns:
            地址信息字典或None
        """
        try:
            import httpx
            from src.config import settings
            
            logger.info(f"尝试获取地址信息: {address}")
            
            # 使用TronGrid API获取真实数据
            api_url = getattr(settings, 'tron_api_url', 'https://api.trongrid.io')
            api_key = getattr(settings, 'tron_api_key', None)
            
            headers = {
                'Accept': 'application/json'
            }
            
            # 尝试使用API密钥
            use_api_key = api_key and api_key.strip()
            if use_api_key:
                headers['TRON-PRO-API-KEY'] = api_key.strip()
                logger.info(f"使用API密钥请求: {api_key[:10]}...")
            else:
                logger.info("使用公共API（无密钥）")
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 获取账户信息
                account_url = f"{api_url}/v1/accounts/{address}"
                logger.info(f"请求TronGrid API: {account_url}")
                
                response = await client.get(account_url, headers=headers)
                
                # 如果401且使用了密钥，尝试不使用密钥（降级到公共API）
                if response.status_code == 401 and use_api_key:
                    logger.warning(f"API密钥无效(401)，尝试使用公共API")
                    headers.pop('TRON-PRO-API-KEY', None)
                    response = await client.get(account_url, headers=headers)
                
                # 如果仍然不是200，记录详细错误并返回None
                if response.status_code != 200:
                    logger.error(
                        f"TronGrid API请求失败: "
                        f"状态码={response.status_code}, "
                        f"URL={account_url}, "
                        f"响应={response.text[:500]}"
                    )
                    return None
                
                data = response.json()
                
                # 解析账户信息
                account_data = data.get('data', [{}])[0] if data.get('data') else {}
                
                # 获取TRX余额（sun转换为TRX）
                trx_balance_sun = account_data.get('balance', 0)
                trx_balance = trx_balance_sun / 1_000_000  # 1 TRX = 1,000,000 sun
                
                # 获取USDT余额（TRC20）
                usdt_balance = 0
                trc20_tokens = account_data.get('trc20', [])
                for token in trc20_tokens:
                    # USDT合约地址: TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
                    if 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t' in str(token):
                        token_value = token.get(list(token.keys())[0], 0)
                        usdt_balance = token_value / 1_000_000  # USDT也是6位小数
                        break
                
                # 获取最近交易（简化版）
                recent_txs = []
                try:
                    tx_url = f"{api_url}/v1/accounts/{address}/transactions"
                    tx_response = await client.get(tx_url, headers=headers, params={'limit': 5})
                    if tx_response.status_code == 200:
                        tx_data = tx_response.json()
                        transactions = tx_data.get('data', [])
                        
                        for tx in transactions[:5]:
                            # 简化交易信息
                            tx_info = {
                                'direction': '转入' if tx.get('to_address') == address else '转出',
                                'amount': '0',
                                'token': 'TRX',
                                'hash': tx.get('txID', '')[:10],
                                'time': tx.get('block_timestamp', '')
                            }
                            recent_txs.append(tx_info)
                except Exception as tx_error:
                    logger.warning(f"获取交易历史失败: {tx_error}")
                
                result = {
                    'trx_balance': f"{trx_balance:.2f}",
                    'usdt_balance': f"{usdt_balance:.2f}",
                    'recent_txs': recent_txs
                }
                
                logger.info(f"成功获取地址信息: TRX={result['trx_balance']}, USDT={result['usdt_balance']}, 交易数={len(recent_txs)}")
                return result
        
        except httpx.TimeoutException as e:
            logger.error(f"API请求超时: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"API请求错误: {e}")
            return None
        except Exception as e:
            logger.error(f"获取地址信息失败: {e}", exc_info=True)
            return None
