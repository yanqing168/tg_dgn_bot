"""
管理面板菜单定义

定义所有管理按钮和菜单结构。
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class AdminMenus:
    """管理面板菜单"""
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """主菜单"""
        keyboard = [
            [InlineKeyboardButton("📊 统计数据", callback_data="admin_stats")],
            [InlineKeyboardButton("💰 价格配置", callback_data="admin_prices")],
            [InlineKeyboardButton("📝 文案配置", callback_data="admin_content")],
            [InlineKeyboardButton("⚙️ 系统设置", callback_data="admin_settings")],
            [InlineKeyboardButton("🚪 退出管理", callback_data="admin_exit")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def price_menu() -> InlineKeyboardMarkup:
        """价格配置菜单"""
        keyboard = [
            [InlineKeyboardButton("💎 Premium 价格", callback_data="admin_price_premium")],
            [InlineKeyboardButton("🔄 TRX 汇率", callback_data="admin_price_trx_rate")],
            [InlineKeyboardButton("⚡ 能量价格", callback_data="admin_price_energy")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="admin_main")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def premium_price_menu() -> InlineKeyboardMarkup:
        """Premium 价格配置菜单"""
        keyboard = [
            [InlineKeyboardButton("✏️ 3个月", callback_data="admin_premium_edit_3")],
            [InlineKeyboardButton("✏️ 6个月", callback_data="admin_premium_edit_6")],
            [InlineKeyboardButton("✏️ 12个月", callback_data="admin_premium_edit_12")],
            [InlineKeyboardButton("🔙 返回", callback_data="admin_prices")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def energy_price_menu() -> InlineKeyboardMarkup:
        """能量价格配置菜单"""
        keyboard = [
            [InlineKeyboardButton("✏️ 小能量", callback_data="admin_energy_edit_small")],
            [InlineKeyboardButton("✏️ 大能量", callback_data="admin_energy_edit_large")],
            [InlineKeyboardButton("✏️ 笔数套餐", callback_data="admin_energy_edit_package")],
            [InlineKeyboardButton("🔙 返回", callback_data="admin_prices")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def content_menu() -> InlineKeyboardMarkup:
        """文案配置菜单"""
        keyboard = [
            [InlineKeyboardButton("👋 欢迎语", callback_data="admin_content_welcome")],
            [InlineKeyboardButton("🎁 免费克隆", callback_data="admin_content_clone")],
            [InlineKeyboardButton("👨‍💼 客服联系", callback_data="admin_content_support")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="admin_main")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def settings_menu() -> InlineKeyboardMarkup:
        """系统设置菜单"""
        keyboard = [
            [InlineKeyboardButton("⏰ 订单超时", callback_data="admin_settings_timeout")],
            [InlineKeyboardButton("🔍 查询限频", callback_data="admin_settings_rate_limit")],
            [InlineKeyboardButton("🧹 清理缓存", callback_data="admin_settings_clear_cache")],
            [InlineKeyboardButton("📊 系统状态", callback_data="admin_settings_status")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="admin_main")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_action(action_data: str) -> InlineKeyboardMarkup:
        """确认操作菜单"""
        keyboard = [
            [
                InlineKeyboardButton("✅ 确认", callback_data=f"admin_confirm_{action_data}"),
                InlineKeyboardButton("❌ 取消", callback_data="admin_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_to_main() -> InlineKeyboardMarkup:
        """返回主菜单按钮"""
        keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="admin_main")]]
        return InlineKeyboardMarkup(keyboard)
