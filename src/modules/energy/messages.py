"""
能量模块消息模板
使用HTML格式
"""


class EnergyMessages:
    """能量兑换的所有消息模板"""
    
    # 主菜单
    MAIN_MENU = """⚡ <b>能量兑换服务</b>

选择兑换类型：

⚡ <b>时长能量（闪租）</b>
  • 6.5万能量 = 3 TRX
  • 13.1万能量 = 6 TRX
  • 有效期：1小时
  • 支付方式：TRX 转账
  • 6秒到账

📦 <b>笔数套餐</b>
  • 弹性笔数：有U扣1笔，无U扣2笔
  • 起售金额：5 USDT
  • 支付方式：USDT 转账
  • 每天至少使用一次

🔄 <b>闪兑</b>
  • USDT 直接兑换能量
  • 支付方式：USDT 转账
  • 订单有效期：{timeout_minutes} 分钟"""

    # 时长能量套餐
    HOURLY_PACKAGES = """⚡ <b>时长能量（闪租）</b>

选择能量套餐：

• <b>6.5万能量</b> = 3 TRX
  有效期：1小时

• <b>13.1万能量</b> = 6 TRX
  有效期：1小时

⚡ 特点：
  • 6秒到账
  • TRX 直接转账
  • 适合临时使用"""

    # 笔数套餐
    PACKAGE_INFO = """📦 <b>笔数套餐</b>

请输入购买金额（USDT）：

💡 <b>套餐说明</b>
  • 起售金额：5 USDT
  • 弹性笔数：有U扣1笔，无U扣2笔
  • 每天至少使用一次
  • USDT 转账支付

请输入金额（例如：10）："""

    # 闪兑
    FLASH_EXCHANGE = """🔄 <b>USDT 闪兑能量</b>

请输入兑换金额（USDT）：

💡 <b>说明</b>
  • USDT 直接兑换能量
  • 实时到账
  • 最低 1 USDT

请输入金额（例如：5）："""

    # 输入地址
    INPUT_ADDRESS = """📍 <b>请输入接收地址</b>

请输入 TRON 地址（T开头）：

⚠️ <b>注意</b>
  • 地址必须是有效的 TRON 地址
  • 请仔细核对，转错无法退回"""

    # 支付信息 - 时长能量
    PAYMENT_INFO_HOURLY = """💳 <b>支付信息</b>

📦 套餐：{energy_amount} 能量
💰 金额：<b>{price} TRX</b>
📍 接收地址：<code>{receive_address}</code>

🏦 <b>付款地址</b>
<code>{payment_address}</code>

⏰ 订单有效期：{timeout_minutes} 分钟
🆔 订单号：<code>{order_id}</code>

⚠️ <b>重要提示</b>
  • 请转账 <b>{price} TRX</b>
  • 转账后自动到账
  • 6秒内完成"""

    # 支付信息 - 笔数套餐/闪兑
    PAYMENT_INFO_USDT = """💳 <b>支付信息</b>

📦 类型：{order_type}
💰 金额：<b>{amount} USDT</b>
📍 接收地址：<code>{receive_address}</code>

🏦 <b>付款地址</b>
<code>{payment_address}</code>

⏰ 订单有效期：{timeout_minutes} 分钟
🆔 订单号：<code>{order_id}</code>

⚠️ <b>重要提示</b>
  • 请转账 <b>{amount} USDT</b>
  • 转账后请提交交易哈希
  • 或点击"已完成转账"按钮"""

    # 等待交易哈希
    WAITING_TX_HASH = """⏳ <b>等待交易确认</b>

订单号：<code>{order_id}</code>

请提交交易哈希（TX Hash）以加快确认：

💡 可以输入交易哈希，或点击"跳过"按钮"""

    # 订单已提交
    ORDER_SUBMITTED = """✅ <b>订单已提交</b>

订单号：<code>{order_id}</code>
交易哈希：<code>{tx_hash}</code>

⏳ 正在处理中，请稍候...

💡 能量将在确认后自动发放到您的地址"""

    # 订单跳过哈希
    ORDER_SKIP_HASH = """✅ <b>订单已提交</b>

订单号：<code>{order_id}</code>

⏳ 系统将自动检测您的转账

💡 能量将在确认后自动发放"""

    # 地址无效
    INVALID_ADDRESS = """❌ <b>地址无效</b>

请输入有效的 TRON 地址（T开头，34位字符）

示例：TYourAddressHere123456789012345"""

    # 金额无效
    INVALID_AMOUNT = """❌ <b>金额无效</b>

{error_message}

请重新输入有效金额"""

    # 取消订单
    ORDER_CANCELLED = """❌ <b>已取消</b>

能量兑换已取消

返回主菜单"""

    # 通用错误
    ERROR_GENERAL = """❌ <b>处理请求时出现错误</b>

错误信息：{error}

请稍后重试或联系客服"""
