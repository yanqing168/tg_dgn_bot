"""
Premium模块键盘布局
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Dict


class PremiumKeyboards:
    """Premium模块的所有键盘布局"""
    
    @staticmethod
    def start_keyboard() -> InlineKeyboardMarkup:
        """开始选择键盘"""
        keyboard = [
            [
                InlineKeyboardButton("💎 给自己开通", callback_data="premium_self"),
                InlineKeyboardButton("🎁 给他人开通", callback_data="premium_other")
            ],
            [
                InlineKeyboardButton("❌ 取消", callback_data="nav_back_to_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def package_keyboard(packages: Dict[int, float]) -> InlineKeyboardMarkup:
        """套餐选择键盘"""
        keyboard = []
        
        # 3个月和6个月在同一行
        row = []
        for months in [3, 6]:
            if months in packages:
                row.append(
                    InlineKeyboardButton(
                        f"{months}个月 - ${packages[months]}", 
                        callback_data=f"premium_{months}"
                    )
                )
        if row:
            keyboard.append(row)
        
        # 12个月单独一行
        if 12 in packages:
            keyboard.append([
                InlineKeyboardButton(
                    f"12个月 - ${packages[12]}", 
                    callback_data="premium_12"
                )
            ])
        
        # 取消按钮
        keyboard.append([
            InlineKeyboardButton("❌ 取消", callback_data="nav_back_to_main")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_user_keyboard() -> InlineKeyboardMarkup:
        """确认用户键盘"""
        keyboard = [
            [
                InlineKeyboardButton("✅ 确认", callback_data="premium_confirm_user"),
                InlineKeyboardButton("🔄 重新输入", callback_data="premium_retry_user")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def retry_or_cancel_keyboard() -> InlineKeyboardMarkup:
        """重试或取消键盘"""
        keyboard = [
            [
                InlineKeyboardButton("🔄 重新输入", callback_data="premium_retry_username"),
                InlineKeyboardButton("❌ 取消", callback_data="nav_back_to_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_order_keyboard() -> InlineKeyboardMarkup:
        """确认订单键盘"""
        keyboard = [
            [
                InlineKeyboardButton("✅ 确认支付", callback_data="premium_confirm_payment"),
                InlineKeyboardButton("❌ 取消订单", callback_data="premium_cancel_order")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_to_main_keyboard() -> InlineKeyboardMarkup:
        """返回主菜单键盘"""
        keyboard = [
            [
                InlineKeyboardButton("🔙 返回主菜单", callback_data="nav_back_to_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
