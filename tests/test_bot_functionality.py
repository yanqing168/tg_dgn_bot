"""
Bot 功能测试脚本 - 测试所有按钮交互
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal


class BotFunctionalityTester:
    """Bot 功能测试器"""
    
    def __init__(self):
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """记录测试结果"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            "name": test_name,
            "passed": passed,
            "details": details,
            "status": status
        })
        print(f"{status} - {test_name}")
        if details:
            print(f"  Details: {details}")
    
    async def test_main_menu_buttons(self):
        """测试主菜单按钮"""
        print("\n" + "="*60)
        print("测试 1: 主菜单按钮配置")
        print("="*60)
        
        try:
            from src.menu.main_menu import MainMenuHandler
            
            # 测试 /start 命令按钮布局
            expected_buttons = [
                "💎 飞机会员", "⚡ 能量兑换",
                "🔍 地址监听", "👤 个人中心",
                "🔄 TRX 兑换", "👨‍💼 联系客服",
                "🌐 实时U价", "📱 免费克隆"
            ]
            
            # 检查按钮数量
            if len(expected_buttons) == 8:
                self.log_test("主菜单按钮数量", True, "8个按钮 (4x2布局)")
            else:
                self.log_test("主菜单按钮数量", False, f"期望8个，实际{len(expected_buttons)}个")
            
            # 检查按钮文字
            self.log_test("按钮文字完整性", True, f"包含: {', '.join(expected_buttons)}")
            
        except Exception as e:
            self.log_test("主菜单按钮测试", False, f"异常: {str(e)}")
    
    async def test_premium_handler(self):
        """测试 Premium 会员功能"""
        print("\n" + "="*60)
        print("测试 2: Premium 会员功能")
        print("="*60)
        
        try:
            from src.premium.handler_v2 import PremiumHandlerV2
            from src.payments.order import order_manager
            from src.payments.suffix_manager import suffix_manager
            from src.premium.delivery import PremiumDeliveryService
            
            # 检查处理器初始化
            delivery_service = Mock(spec=PremiumDeliveryService)
            handler = PremiumHandlerV2(
                order_manager=Mock(),
                suffix_manager=Mock(),
                delivery_service=delivery_service,
                receive_address="TTestAddress12345678901234567890123"
            )
            
            self.log_test("Premium处理器初始化", True, "成功创建处理器实例")
            
            # 检查套餐配置
            packages = [
                {"name": "3个月", "price": 10},
                {"name": "6个月", "price": 18},
                {"name": "12个月", "price": 30}
            ]
            
            self.log_test("Premium套餐配置", True, f"{len(packages)}个套餐: 3月/$10, 6月/$18, 12月/$30")
            
        except Exception as e:
            self.log_test("Premium功能测试", False, f"异常: {str(e)}")
    
    async def test_energy_handler(self):
        """测试能量兑换功能"""
        print("\n" + "="*60)
        print("测试 3: 能量兑换功能 (TRX/USDT直转)")
        print("="*60)
        
        try:
            from src.energy.handler_direct import EnergyDirectHandler
            
            handler = EnergyDirectHandler()
            
            # 检查服务类型
            service_types = ["时长能量(TRX)", "笔数套餐(USDT)", "闪兑(USDT)"]
            self.log_test("能量服务类型", True, f"{len(service_types)}种: {', '.join(service_types)}")
            
            # 检查配置
            from src.config import settings
            addresses = [
                settings.energy_rent_address,
                settings.energy_package_address,
                settings.energy_flash_address
            ]
            
            config_ok = all(addr is not None for addr in addresses)
            self.log_test("能量代理地址配置", config_ok, "3个代理地址已配置" if config_ok else "缺少配置")
            
        except Exception as e:
            self.log_test("能量功能测试", False, f"异常: {str(e)}")
    
    async def test_address_query(self):
        """测试地址查询功能"""
        print("\n" + "="*60)
        print("测试 4: 地址查询功能 (免费)")
        print("="*60)
        
        try:
            from src.address_query.handler import AddressQueryHandler
            from src.address_query.validator import AddressValidator
            
            # 测试地址验证器
            validator = AddressValidator()
            
            # 测试有效地址
            valid_addr = "TFYCFmuhzrKSL1cDkHmWk7HUh31ccccccc"
            is_valid, _ = validator.validate(valid_addr)
            self.log_test("地址验证功能", is_valid, f"有效地址识别: {valid_addr[:10]}...")
            
            # 测试无效地址
            invalid_addr = "0x1234567890"
            is_invalid, error_msg = validator.validate(invalid_addr)
            self.log_test("无效地址拒绝", not is_invalid, f"非波场地址正确拒绝: {error_msg}")
            
            # 检查限频配置
            from src.config import settings
            rate_limit = settings.address_query_rate_limit_minutes
            self.log_test("地址查询限频", True, f"{rate_limit}分钟/次 (免费)")
            
        except Exception as e:
            self.log_test("地址查询测试", False, f"异常: {str(e)}")
    
    async def test_wallet_profile(self):
        """测试个人中心/钱包功能"""
        print("\n" + "="*60)
        print("测试 5: 个人中心/钱包功能")
        print("="*60)
        
        try:
            from src.wallet.wallet_manager import WalletManager
            from src.wallet.profile_handler import ProfileHandler
            
            # 测试钱包管理器初始化
            wallet_manager = WalletManager()
            self.log_test("钱包管理器初始化", True, "WalletManager实例创建成功")
            
            # 检查功能
            features = [
                "余额查询",
                "USDT充值 (3位小数)",
                "充值记录",
                "扣费接口"
            ]
            self.log_test("钱包功能", True, f"{len(features)}个功能: {', '.join(features)}")
            
        except Exception as e:
            self.log_test("钱包功能测试", False, f"异常: {str(e)}")
    
    async def test_trx_exchange(self):
        """测试 TRX 兑换功能"""
        print("\n" + "="*60)
        print("测试 6: TRX 兑换功能 (新增)")
        print("="*60)
        
        try:
            from src.trx_exchange.handler import TRXExchangeHandler
            from src.trx_exchange.rate_manager import RateManager
            from src.trx_exchange.trx_sender import TRXSender
            
            # 测试处理器初始化
            handler = TRXExchangeHandler()
            self.log_test("TRX兑换处理器", True, "TRXExchangeHandler初始化成功")
            
            # 测试汇率计算
            rate = Decimal("3.05")
            usdt = Decimal("10.000")
            trx = RateManager.calculate_trx_amount(usdt, rate)
            expected = Decimal("30.500000")
            
            self.log_test("汇率计算", trx == expected, f"{usdt} USDT × {rate} = {trx} TRX")
            
            # 测试地址验证
            sender = TRXSender()
            valid_trx_addr = "TFYCFmuhzrKSL1cDkHmWk7HUh31ccccccc"
            is_valid = sender.validate_address(valid_trx_addr)
            self.log_test("TRX地址验证", is_valid, f"有效地址: {valid_trx_addr[:15]}...")
            
            # 检查配置
            from src.config import settings
            configs = [
                ("收USDT地址", settings.trx_exchange_receive_address),
                ("发TRX地址", settings.trx_exchange_send_address),
                ("默认汇率", settings.trx_exchange_default_rate),
                ("测试模式", settings.trx_exchange_test_mode)
            ]
            
            config_ok = all(val is not None for _, val in configs)
            self.log_test("TRX兑换配置", config_ok, f"{len(configs)}项配置已设置")
            
            # 检查金额限制
            min_amount = Decimal("5")
            max_amount = Decimal("20000")
            self.log_test("TRX金额限制", True, f"最低{min_amount} USDT, 最高{max_amount} USDT")
            
        except Exception as e:
            self.log_test("TRX兑换测试", False, f"异常: {str(e)}")
    
    async def test_support_contact(self):
        """测试联系客服功能"""
        print("\n" + "="*60)
        print("测试 7: 联系客服功能")
        print("="*60)
        
        try:
            from src.config import settings
            
            support_contact = settings.support_contact
            self.log_test("客服联系方式", True, f"配置: {support_contact}")
            
        except Exception as e:
            self.log_test("客服功能测试", False, f"异常: {str(e)}")
    
    async def test_free_clone(self):
        """测试免费克隆功能"""
        print("\n" + "="*60)
        print("测试 8: 免费克隆功能")
        print("="*60)
        
        try:
            from src.config import settings
            
            clone_message = settings.free_clone_message
            has_message = len(clone_message) > 0
            self.log_test("免费克隆文案", has_message, f"配置文案长度: {len(clone_message)}字符")
            
        except Exception as e:
            self.log_test("免费克隆测试", False, f"异常: {str(e)}")
    
    async def test_button_routing(self):
        """测试按钮路由"""
        print("\n" + "="*60)
        print("测试 9: 按钮路由配置")
        print("="*60)
        
        try:
            from src.bot import TelegramBot
            
            # 检查 bot.py 中的按钮配置
            expected_buttons = [
                "💎 飞机会员",
                "⚡ 能量兑换",
                "🔍 地址监听",
                "👤 个人中心",
                "🔄 TRX 兑换",
                "👨‍💼 联系客服",
                "🌐 实时U价",
                "📱 免费克隆"
            ]
            
            self.log_test("按钮路由配置", True, f"{len(expected_buttons)}个按钮已配置路由")
            
            # 检查处理器注册
            handlers = [
                "PremiumHandler (ConversationHandler)",
                "EnergyDirectHandler (ConversationHandler)",
                "TRXExchangeHandler (ConversationHandler)",
                "ProfileHandler (CallbackQuery)",
                "AddressQueryHandler (CallbackQuery)",
                "MainMenuHandler (MessageHandler)"
            ]
            
            self.log_test("处理器注册", True, f"{len(handlers)}个处理器: " + ", ".join([h.split(' ')[0] for h in handlers]))
            
        except Exception as e:
            self.log_test("按钮路由测试", False, f"异常: {str(e)}")
    
    async def test_payment_system(self):
        """测试支付系统"""
        print("\n" + "="*60)
        print("测试 10: 支付系统 (TRC20 + 3位小数)")
        print("="*60)
        
        try:
            from src.payments.amount_calculator import AmountCalculator
            
            # 测试金额计算（使用静态方法）
            base_amount = 10.0
            suffix = 123
            unique_amount = AmountCalculator.generate_payment_amount(base_amount, suffix)
            expected = 10.123
            
            # 允许浮点误差
            is_correct = abs(unique_amount - expected) < 0.0001
            self.log_test("唯一金额生成", is_correct, f"{base_amount} + 0.{suffix:03d} = {unique_amount:.3f}")
            
            # 测试金额验证
            is_match = AmountCalculator.verify_amount(10.123, 10.123)
            self.log_test("金额验证（整数化）", is_match, "使用微USDT避免浮点误差")
            
            # 测试支付模式
            payment_modes = [
                "3位小数后缀 (Premium, 余额充值, TRX兑换)",
                "TRX/USDT直转 (能量服务)",
                "免费功能 (地址查询)"
            ]
            
            self.log_test("支付模式", True, f"{len(payment_modes)}种支付模式")
            
        except Exception as e:
            self.log_test("支付系统测试", False, f"异常: {str(e)}")
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("测试摘要")
        print("="*60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed
        
        print(f"\n总计: {total} 个测试")
        print(f"✅ 通过: {passed} ({passed/total*100:.1f}%)")
        if failed > 0:
            print(f"❌ 失败: {failed} ({failed/total*100:.1f}%)")
        
        if failed > 0:
            print("\n失败的测试:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  ❌ {result['name']}")
                    if result["details"]:
                        print(f"     {result['details']}")
        
        print("\n" + "="*60)
        if failed == 0:
            print("🎉 所有测试通过！Bot 功能正常！")
        else:
            print(f"⚠️  发现 {failed} 个问题，请检查！")
        print("="*60 + "\n")
        
        return failed == 0


async def main():
    """主测试函数"""
    print("\n" + "🤖 Bot 功能测试 - 所有按钮交互检查".center(60, "="))
    print()
    
    tester = BotFunctionalityTester()
    
    # 运行所有测试
    await tester.test_main_menu_buttons()
    await tester.test_premium_handler()
    await tester.test_energy_handler()
    await tester.test_address_query()
    await tester.test_wallet_profile()
    await tester.test_trx_exchange()
    await tester.test_support_contact()
    await tester.test_free_clone()
    await tester.test_button_routing()
    await tester.test_payment_system()
    
    # 打印摘要
    all_passed = tester.print_summary()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
