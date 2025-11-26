"""
地址查询模块键盘布局
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class AddressQueryKeyboards:
    """地址查询键盘类"""
    
    @staticmethod
    def cancel_keyboard() -> InlineKeyboardMarkup:
        """取消键盘"""
        keyboard = [[
            InlineKeyboardButton("❌ 取消", callback_data="addrq_cancel")
        ]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_to_main_keyboard() -> InlineKeyboardMarkup:
        """返回主菜单键盘"""
        keyboard = [[
            InlineKeyboardButton("🔙 返回主菜单", callback_data="addrq_back_to_main")
        ]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def result_keyboard(overview_url: str, txs_url: str) -> InlineKeyboardMarkup:
        """查询结果键盘"""
        keyboard = [
            [
                InlineKeyboardButton("🔗 链上查询详情", url=overview_url),
                InlineKeyboardButton("🔍 查询转账记录", url=txs_url),
            ],
            [
                InlineKeyboardButton("🔙 返回主菜单", callback_data="addrq_back_to_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def retry_keyboard() -> InlineKeyboardMarkup:
        """重试键盘"""
        keyboard = [
            [
                InlineKeyboardButton("🔄 重新查询", callback_data="addrq_retry"),
                InlineKeyboardButton("🔙 返回主菜单", callback_data="addrq_back_to_main"),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
