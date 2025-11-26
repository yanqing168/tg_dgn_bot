"""
管理员订单查询处理器
仅 BOT_OWNER_ID 可访问
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, or_
from loguru import logger

from src.config import settings
from src.database import SessionLocal, Order

# 会话状态
SHOW_ORDERS, FILTER_BY_TYPE, FILTER_BY_STATUS, SHOW_DETAIL = range(4)

# 订单类型映射
ORDER_TYPE_NAMES = {
    "premium": "🎁 Premium会员",
    "deposit": "💰 余额充值",
    "trx_exchange": "⚡ TRX兑换",
    "energy": "🔋 能量服务"
}

# 订单状态映射
ORDER_STATUS_NAMES = {
    "PENDING": "⏳ 待支付",
    "PAID": "✅ 已支付",
    "DELIVERED": "🎉 已交付",
    "EXPIRED": "⏰ 已过期",
    "CANCELLED": "❌ 已取消"
}


def _format_datetime(value: Optional[datetime]) -> str:
    """将时间格式化为统一字符串"""
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else "-"


def _format_amount(micro_amount: Optional[int]) -> str:
    """格式化微 USDT 金额"""
    if micro_amount is None:
        return "-"
    return f"{micro_amount / 1_000_000:.3f} USDT"


def _mask_tx_hash(tx_hash: str) -> str:
    """使用固定前缀/后缀掩码交易哈希"""
    if not tx_hash or len(tx_hash) <= 10:
        return tx_hash
    return f"{tx_hash[:6]}...{tx_hash[-4:]}"


def _build_order_detail_text(order: Order) -> str:
    """构建订单详情文本，供管理员查看"""
    order_type = ORDER_TYPE_NAMES.get(order.order_type, order.order_type)
    status = ORDER_STATUS_NAMES.get(order.status, order.status)

    lines = [
        "📦 **订单详情**",
        f"🔑 订单号：`{order.order_id}`",
        f"👤 用户：{order.user_id}",
        f"📦 类型：{order_type}",
        f"📊 状态：{status}",
        f"💵 金额：{_format_amount(getattr(order, 'amount_usdt', None))}",
    ]

    if getattr(order, "recipient", None):
        lines.append(f"🎯 目标：{order.recipient}")

    if getattr(order, "premium_months", None):
        lines.append(f"📅 Premium：{order.premium_months} 个月")

    # 时间线
    lines.extend([
        "",
        "🕒 **时间线**",
        f"• 创建：{_format_datetime(getattr(order, 'created_at', None))}",
        f"• 支付：{_format_datetime(getattr(order, 'paid_at', None))}",
        f"• 交付：{_format_datetime(getattr(order, 'delivered_at', None))}",
        f"• 过期：{_format_datetime(getattr(order, 'expires_at', None))}",
    ])

    # 用户确认信息
    has_user_confirmation = any([
        getattr(order, "user_confirmed_at", None),
        getattr(order, "user_confirm_source", None),
    ])
    if has_user_confirmation:
        lines.extend([
            "",
            "👤 用户确认",
        ])
        if getattr(order, "user_confirm_source", None):
            lines.append(f"• 来源：{order.user_confirm_source}")
        if getattr(order, "user_confirmed_at", None):
            lines.append(f"• 时间：{_format_datetime(order.user_confirmed_at)}")

    if getattr(order, "user_tx_hash", None):
        lines.extend([
            "",
            "🧾 用户填写 TX Hash",
            f"`{_mask_tx_hash(order.user_tx_hash)}`",
        ])

    if getattr(order, "tx_hash", None):
        lines.extend([
            "",
            "🔗 系统 TX Hash",
            f"`{_mask_tx_hash(order.tx_hash)}`",
        ])

    return "\n".join(lines)


def owner_only(func):
    """装饰器：仅 Owner 可访问"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != settings.bot_owner_id:
            await update.message.reply_text("❌ 此命令仅限管理员使用")
            return ConversationHandler.END
        return await func(update, context, *args, **kwargs)
    return wrapper


async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """订单查询命令入口（管理员专用）"""
    user_id = update.effective_user.id
    if user_id != settings.bot_owner_id:
        await update.message.reply_text("❌ 此命令仅限管理员使用")
        return ConversationHandler.END
    
    # 初始化过滤器
    context.user_data['order_filters'] = {
        'order_type': None,
        'status': None,
        'user_id': None,
        'page': 1,
        'per_page': 10
    }
    
    # 显示主菜单
    return await show_orders_menu(update, context)


async def show_orders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """显示订单管理主菜单"""
    filters = context.user_data.get('order_filters', {})
    
    # 查询订单统计
    session = SessionLocal()
    try:
        # 总订单数
        total_count = session.query(func.count(Order.order_id)).scalar()
        
        # 各状态订单数
        pending_count = session.query(func.count(Order.order_id)).filter(Order.status == "PENDING").scalar()
        paid_count = session.query(func.count(Order.order_id)).filter(Order.status == "PAID").scalar()
        delivered_count = session.query(func.count(Order.order_id)).filter(Order.status == "DELIVERED").scalar()
        expired_count = session.query(func.count(Order.order_id)).filter(Order.status == "EXPIRED").scalar()
        
        # 各类型订单数
        premium_count = session.query(func.count(Order.order_id)).filter(Order.order_type == "premium").scalar()
        deposit_count = session.query(func.count(Order.order_id)).filter(Order.order_type == "deposit").scalar()
        trx_count = session.query(func.count(Order.order_id)).filter(Order.order_type == "trx_exchange").scalar()
        energy_count = session.query(func.count(Order.order_id)).filter(Order.order_type == "energy").scalar()
        
    finally:
        session.close()
    
    # 构建消息
    text = (
        "📊 **订单管理系统（管理员）**\n\n"
        f"📈 **订单统计**\n"
        f"├─ 总订单数：{total_count} 个\n"
        f"├─ ⏳ 待支付：{pending_count} 个\n"
        f"├─ ✅ 已支付：{paid_count} 个\n"
        f"├─ 🎉 已交付：{delivered_count} 个\n"
        f"└─ ⏰ 已过期：{expired_count} 个\n\n"
        f"📦 **订单类型**\n"
        f"├─ 🎁 Premium：{premium_count} 个\n"
        f"├─ 💰 充值：{deposit_count} 个\n"
        f"├─ ⚡ TRX兑换：{trx_count} 个\n"
        f"└─ 🔋 能量：{energy_count} 个\n\n"
    )
    
    # 显示当前筛选条件
    if any(filters.values()):
        text += "🔍 **当前筛选**\n"
        if filters.get('order_type'):
            text += f"├─ 类型：{ORDER_TYPE_NAMES.get(filters['order_type'], filters['order_type'])}\n"
        if filters.get('status'):
            text += f"├─ 状态：{ORDER_STATUS_NAMES.get(filters['status'], filters['status'])}\n"
        if filters.get('user_id'):
            text += f"└─ 用户ID：{filters['user_id']}\n"
        text += "\n"
    
    text += "请选择操作："
    
    # 构建按钮
    keyboard = [
        [
            InlineKeyboardButton("📋 查看订单列表", callback_data="orders_list"),
            InlineKeyboardButton("🔍 按类型筛选", callback_data="orders_filter_type")
        ],
        [
            InlineKeyboardButton("📊 按状态筛选", callback_data="orders_filter_status"),
            InlineKeyboardButton("👤 按用户筛选", callback_data="orders_filter_user")
        ],
        [
            InlineKeyboardButton("🔄 清除筛选", callback_data="orders_clear_filter"),
            InlineKeyboardButton("❌ 关闭", callback_data="orders_close")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 发送或编辑消息
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    return SHOW_ORDERS


async def show_orders_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """显示订单列表"""
    query = update.callback_query
    await query.answer()
    
    filters = context.user_data.get('order_filters', {})
    page = filters.get('page', 1)
    per_page = filters.get('per_page', 10)
    
    session = SessionLocal()
    try:
        # 构建查询条件
        conditions = []
        if filters.get('order_type'):
            conditions.append(Order.order_type == filters['order_type'])
        if filters.get('status'):
            conditions.append(Order.status == filters['status'])
        if filters.get('user_id'):
            conditions.append(Order.user_id == filters['user_id'])
        
        # 查询订单
        stmt = select(Order).order_by(Order.created_at.desc())
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        # 分页
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)
        
        orders = session.execute(stmt).scalars().all()
        
        # 查询总数
        count_stmt = select(func.count(Order.order_id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total_count = session.execute(count_stmt).scalar()
        
    finally:
        session.close()
    
    # 构建消息
    total_pages = (total_count + per_page - 1) // per_page
    
    text = f"📋 **订单列表** (第 {page}/{total_pages} 页)\n\n"
    
    if not orders:
        text += "暂无订单数据\n"
    else:
        for order in orders:
            order_type_name = ORDER_TYPE_NAMES.get(order.order_type, order.order_type)
            status_name = ORDER_STATUS_NAMES.get(order.status, order.status)
            amount = order.amount_usdt / 1_000_000
            created_time = order.created_at.strftime('%m-%d %H:%M')
            
            text += (
                f"🔹 `{order.order_id}`\n"
                f"   {order_type_name} | {status_name}\n"
                f"   💵 {amount:.3f} USDT | 👤 {order.user_id}\n"
                f"   🕐 {created_time}\n\n"
            )
    
    text += f"\n📊 共 {total_count} 个订单"
    
    # 构建按钮
    keyboard = []
    
    # 分页按钮
    page_buttons = []
    if page > 1:
        page_buttons.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"orders_page_{page-1}"))
    if page < total_pages:
        page_buttons.append(InlineKeyboardButton("➡️ 下一页", callback_data=f"orders_page_{page+1}"))
    if page_buttons:
        keyboard.append(page_buttons)
    
    # 操作按钮
    keyboard.append([
        InlineKeyboardButton("🔙 返回", callback_data="orders_back"),
        InlineKeyboardButton("❌ 关闭", callback_data="orders_close")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SHOW_ORDERS


async def filter_by_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """按订单类型筛选"""
    query = update.callback_query
    await query.answer()
    
    text = "🔍 **按订单类型筛选**\n\n请选择订单类型："
    
    keyboard = [
        [
            InlineKeyboardButton("🎁 Premium会员", callback_data="orders_type_premium"),
            InlineKeyboardButton("💰 余额充值", callback_data="orders_type_deposit")
        ],
        [
            InlineKeyboardButton("⚡ TRX兑换", callback_data="orders_type_trx_exchange"),
            InlineKeyboardButton("🔋 能量服务", callback_data="orders_type_energy")
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data="orders_back"),
            InlineKeyboardButton("❌ 关闭", callback_data="orders_close")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return SHOW_ORDERS


async def filter_by_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """按订单状态筛选"""
    query = update.callback_query
    await query.answer()
    
    text = "📊 **按订单状态筛选**\n\n请选择订单状态："
    
    keyboard = [
        [
            InlineKeyboardButton("⏳ 待支付", callback_data="orders_status_PENDING"),
            InlineKeyboardButton("✅ 已支付", callback_data="orders_status_PAID")
        ],
        [
            InlineKeyboardButton("🎉 已交付", callback_data="orders_status_DELIVERED"),
            InlineKeyboardButton("⏰ 已过期", callback_data="orders_status_EXPIRED")
        ],
        [
            InlineKeyboardButton("❌ 已取消", callback_data="orders_status_CANCELLED")
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data="orders_back"),
            InlineKeyboardButton("❌ 关闭", callback_data="orders_close")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return SHOW_ORDERS


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理回调查询"""
    query = update.callback_query
    
    # H2 安全加固：管理员权限校验
    user_id = update.effective_user.id
    if user_id != settings.bot_owner_id:
        await query.answer("⛔ 权限不足", show_alert=True)
        return ConversationHandler.END
    
    data = query.data
    
    filters = context.user_data.get('order_filters', {})
    
    # 查看订单列表
    if data == "orders_list":
        return await show_orders_list(update, context)
    
    # 筛选操作
    elif data == "orders_filter_type":
        return await filter_by_type(update, context)
    elif data == "orders_filter_status":
        return await filter_by_status(update, context)
    elif data == "orders_filter_user":
        await query.answer("💡 提示：请使用命令 /orders user_id=123456 按用户筛选")
        return SHOW_ORDERS
    
    # 设置类型筛选
    elif data.startswith("orders_type_"):
        order_type = data.replace("orders_type_", "")
        filters['order_type'] = order_type
        filters['page'] = 1  # 重置页码
        context.user_data['order_filters'] = filters
        await query.answer(f"✅ 已筛选：{ORDER_TYPE_NAMES.get(order_type, order_type)}")
        return await show_orders_menu(update, context)
    
    # 设置状态筛选
    elif data.startswith("orders_status_"):
        status = data.replace("orders_status_", "")
        filters['status'] = status
        filters['page'] = 1  # 重置页码
        context.user_data['order_filters'] = filters
        await query.answer(f"✅ 已筛选：{ORDER_STATUS_NAMES.get(status, status)}")
        return await show_orders_menu(update, context)
    
    # 分页
    elif data.startswith("orders_page_"):
        page = int(data.replace("orders_page_", ""))
        filters['page'] = page
        context.user_data['order_filters'] = filters
        return await show_orders_list(update, context)
    
    # 清除筛选
    elif data == "orders_clear_filter":
        filters['order_type'] = None
        filters['status'] = None
        filters['user_id'] = None
        filters['page'] = 1
        context.user_data['order_filters'] = filters
        await query.answer("✅ 已清除所有筛选条件")
        return await show_orders_menu(update, context)
    
    # 返回主菜单
    elif data == "orders_back":
        return await show_orders_menu(update, context)
    
    # 关闭
    elif data == "orders_close":
        await query.answer()
        await query.delete_message()
        return ConversationHandler.END
    
    return SHOW_ORDERS


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """取消会话"""
    if update.message:
        await update.message.reply_text("已取消订单查询")
    return ConversationHandler.END


def get_orders_handler() -> ConversationHandler:
    """获取订单查询处理器"""
    return ConversationHandler(
        entry_points=[CommandHandler("orders", orders_command)],
        states={
            SHOW_ORDERS: [
                CallbackQueryHandler(handle_callback, pattern=r"^orders_")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(handle_callback, pattern=r"^orders_close$"),
            CommandHandler("cancel", cancel)
        ],
        per_chat=True,
        per_user=True,
        per_message=False,
        allow_reentry=True,
    )
