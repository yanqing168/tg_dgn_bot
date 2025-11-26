"""
能量模块键盘布局
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class EnergyKeyboards:
    """能量模块的所有键盘布局"""
    
    @staticmethod
    def main_menu():
        """主菜单键盘"""
        keyboard = [
            [InlineKeyboardButton("⚡ 时长能量（闪租）", callback_data="energy_type_hourly")],
            [InlineKeyboardButton("📦 笔数套餐", callback_data="energy_type_package")],
            [InlineKeyboardButton("🔄 闪兑", callback_data="energy_type_flash")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def hourly_packages():
        """时长能量套餐键盘"""
        keyboard = [
            [InlineKeyboardButton("⚡ 6.5万能量 (3 TRX)", callback_data="energy_pkg_65k")],
            [InlineKeyboardButton("⚡ 13.1万能量 (6 TRX)", callback_data="energy_pkg_131k")],
            [InlineKeyboardButton("🔙 返回", callback_data="energy_back")],
            [InlineKeyboardButton("❌ 取消", callback_data="energy_cancel")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def payment_done():
        """支付完成键盘"""
        keyboard = [
            [InlineKeyboardButton("✅ 已完成转账", callback_data="energy_payment_done")],
            [InlineKeyboardButton("❌ 取消订单", callback_data="energy_cancel")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def skip_tx_hash():
        """跳过交易哈希键盘"""
        keyboard = [
            [InlineKeyboardButton("⏭️ 跳过", callback_data="energy_skip_hash")],
            [InlineKeyboardButton("❌ 取消", callback_data="energy_cancel")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_and_cancel():
        """返回和取消键盘"""
        keyboard = [
            [InlineKeyboardButton("🔙 返回", callback_data="energy_back")],
            [InlineKeyboardButton("❌ 取消", callback_data="energy_cancel")],
        ]
        return InlineKeyboardMarkup(keyboard)
