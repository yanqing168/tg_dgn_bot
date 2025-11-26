"""
Premium模块状态定义
与原handler_v2.py保持一致
"""

# 对话状态
SELECTING_TARGET = 0       # 选择给自己还是他人
SELECTING_PACKAGE = 1      # 选择套餐
ENTERING_USERNAME = 2      # 输入他人用户名
AWAITING_USERNAME_ACTION = 3  # 等待用户名操作（重试或取消）
VERIFYING_USERNAME = 4     # 验证用户名
CONFIRMING_ORDER = 5       # 确认订单
PROCESSING_PAYMENT = 6     # 处理支付
