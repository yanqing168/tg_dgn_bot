"""
通用装饰器模块
提供错误处理、日志记录等装饰器
"""
import functools
import logging
from typing import Callable, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

logger = logging.getLogger(__name__)


def error_handler(func: Callable) -> Callable:
    """
    错误处理装饰器
    捕获异常并发送友好的错误消息给用户
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # 处理实例方法和静态方法
        if len(args) >= 2 and isinstance(args[0], Update):
            update, context = args[0], args[1]
        elif len(args) >= 3:
            # 实例方法 (self, update, context)
            update, context = args[1], args[2]
        else:
            # 无法识别参数，直接执行
            return await func(*args, **kwargs)
            
        try:
            # 记录函数调用
            user = update.effective_user
            if user:
                logger.info(
                    f"用户 {user.id} ({user.username or user.first_name}) 调用 {func.__name__}"
                )
            
            # 执行原函数
            result = await func(*args, **kwargs)
            
            # 记录成功
            logger.debug(f"{func.__name__} 执行成功")
            return result
            
        except Exception as e:
            # 记录错误
            logger.error(
                f"{func.__name__} 执行失败: {e}", 
                exc_info=True,
                extra={
                    'user_id': update.effective_user.id if update.effective_user else None,
                    'function': func.__name__,
                    'func_module': func.__module__  # 避免与内置的module冲突
                }
            )
            
            # 收集错误到错误收集器
            try:
                from src.common.error_collector import collect_error
                collect_error(
                    error_type=f"{func.__module__}.{func.__name__}",
                    message=str(e),
                    context={
                        'user_id': update.effective_user.id if update.effective_user else None,
                        'username': update.effective_user.username if update.effective_user else None,
                        'function': func.__name__,
                        'module': func.__module__
                    },
                    exception=e
                )
            except:
                pass  # 错误收集器本身出错不应影响主流程
            
            # 发送错误消息给用户
            error_msg = (
                "❌ <b>操作失败</b>\n\n"
                "系统处理您的请求时遇到错误。\n"
                "请稍后重试或联系客服。\n\n"
                f"错误代码: <code>{func.__name__}_{type(e).__name__}</code>"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                if update.message:
                    await update.message.reply_text(
                        error_msg,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                elif update.callback_query:
                    await update.callback_query.answer("❌ 操作失败，请重试")
                    await update.callback_query.edit_message_text(
                        error_msg,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
            except Exception as send_error:
                logger.error(f"发送错误消息失败: {send_error}")
            
            # 返回END状态结束对话
            return ConversationHandler.END
            
    return wrapper


def log_action(action_name: str = None):
    """
    操作日志装饰器
    记录用户操作和结果
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取update和context
            if len(args) >= 2 and isinstance(args[0], Update):
                update = args[0]
            elif len(args) >= 3:
                update = args[1]
            else:
                return await func(*args, **kwargs)
            
            user = update.effective_user
            name = action_name or func.__name__
            
            # 记录操作开始
            logger.info(
                f"[ACTION_START] {name} - 用户: {user.id if user else 'Unknown'}"
            )
            
            try:
                result = await func(*args, **kwargs)
                # 记录操作成功
                logger.info(
                    f"[ACTION_SUCCESS] {name} - 用户: {user.id if user else 'Unknown'}"
                )
                return result
            except Exception as e:
                # 记录操作失败
                logger.error(
                    f"[ACTION_FAILED] {name} - 用户: {user.id if user else 'Unknown'} - 错误: {e}"
                )
                raise
                
        return wrapper
    return decorator


def require_private_chat(func: Callable) -> Callable:
    """
    要求私聊装饰器
    确保命令只在私聊中执行
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_chat.type != 'private':
            await update.message.reply_text(
                "⚠️ 此功能仅支持私聊使用。\n"
                "请私聊我后重试。"
            )
            return ConversationHandler.END
        return await func(update, context, *args, **kwargs)
    return wrapper
