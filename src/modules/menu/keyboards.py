"""
主菜单模块键盘布局
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


class MenuKeyboards:
    """主菜单键盘类"""
    
    @staticmethod
    def main_menu_inline() -> InlineKeyboardMarkup:
        """主菜单内联键盘"""
        keyboard = [
            [
                InlineKeyboardButton("💎 Premium 开通", callback_data="menu_premium"),
                InlineKeyboardButton("⚡ 能量兑换", callback_data="menu_energy"),
            ],
            [
                InlineKeyboardButton("💱 TRX 兑换", callback_data="menu_trx"),
                InlineKeyboardButton("🔍 地址查询", callback_data="menu_address"),
            ],
            [
                InlineKeyboardButton("💰 我的钱包", callback_data="menu_wallet"),
                InlineKeyboardButton("📋 我的订单", callback_data="menu_orders"),
            ],
            [
                InlineKeyboardButton("❓ 帮助", callback_data="menu_help"),
                InlineKeyboardButton("📞 联系客服", callback_data="menu_support"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def main_menu_reply() -> ReplyKeyboardMarkup:
        """主菜单回复键盘"""
        keyboard = [
            [KeyboardButton("💎 Premium"), KeyboardButton("⚡ 能量")],
            [KeyboardButton("💱 TRX兑换"), KeyboardButton("🔍 地址查询")],
            [KeyboardButton("💰 钱包"), KeyboardButton("📋 订单")],
            [KeyboardButton("❓ 帮助")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def back_to_main() -> InlineKeyboardMarkup:
        """返回主菜单按钮"""
        keyboard = [[
            InlineKeyboardButton("🔙 返回主菜单", callback_data="menu_back_to_main")
        ]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def cancel_button() -> InlineKeyboardMarkup:
        """取消按钮"""
        keyboard = [[
            InlineKeyboardButton("❌ 取消", callback_data="menu_cancel")
        ]]
        return InlineKeyboardMarkup(keyboard)
