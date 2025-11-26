"""
Premium模块消息模板
使用HTML格式，避免Markdown解析错误
"""


class PremiumMessages:
    """Premium模块的所有消息模板"""
    
    # 开始界面
    START = """🎁 <b>Premium 会员开通</b>

请选择开通方式：
• 给自己开通 - 为您的账号开通Premium
• 给他人开通 - 为指定用户开通Premium

💰 套餐价格：
• 3个月 - ${price_3} USDT
• 6个月 - ${price_6} USDT
• 12个月 - ${price_12} USDT"""

    # 给自己开通
    SELECT_SELF = """✅ <b>为自己开通 Premium</b>

👤 开通账号：
• 用户名：{username}
• 昵称：{nickname}

📦 请选择套餐时长："""

    # 给他人开通
    SELECT_OTHER = """🎁 <b>为他人开通 Premium</b>

请输入对方的 Telegram 用户名：
• 支持格式：@username 或 username
• 用户名需为 5-32 个字符
• 仅支持字母、数字和下划线

示例：@alice 或 alice"""

    # 用户名格式无效
    INVALID_USERNAME = """❌ 用户名格式无效！

用户名需要：
• 5-32个字符
• 仅包含字母、数字、下划线

请重新输入："""

    # 找到用户
    USER_FOUND = """✅ <b>找到用户</b>

用户名：@{username}
昵称：{nickname}

确认为此用户开通 Premium？"""

    # 用户未找到
    USER_NOT_FOUND = """⚠️ <b>用户 @{username} 未找到</b>

可能原因：
• 用户名输入错误
• 用户未与本Bot交互过

请让对方先点击以下链接与Bot交互：
{binding_url}"""

    # 用户未验证
    USER_NOT_VERIFIED = """⚠️ <b>用户 @{username} 未验证</b>

请让对方先与Bot交互进行验证"""

    # 为他人开通确认
    SELECT_OTHER_CONFIRM = """🎁 <b>为他人开通 Premium</b>

👤 接收用户：
• 用户名：@{username}
• 昵称：{nickname}

📦 请选择套餐时长："""

    # 订单确认
    ORDER_CONFIRM = """📦 <b>订单确认</b>

套餐：{months} 个月 Premium
{recipient_info}

💰 应付金额：<code>{amount:.3f}</code> USDT (TRC20)
📍 收款地址：<code>{address}</code>

⏰ 订单有效期：{remaining} 分钟
📝 订单号：<code>{order_id}</code>"""

    # 订单已创建
    ORDER_CREATED = """✅ <b>订单已创建</b>

💰 应付金额：<code>{amount:.3f}</code> USDT
📍 收款地址：<code>{address}</code>

⚠️ 请精确转账 <code>{amount:.3f}</code> USDT（包含小数部分）
⏰ 支付后 2-5 分钟内自动到账

🔖 订单号：<code>{order_id}</code>"""

    # 订单已取消
    ORDER_CANCELLED = """❌ 订单已取消"""

    # 错误消息
    ERROR_GENERAL = """❌ 处理请求时出现错误，请稍后重试或联系客服。

错误详情：{error}"""

    # 创建订单失败
    ERROR_CREATE_ORDER = """❌ 创建订单失败，请稍后重试或联系客服。"""
