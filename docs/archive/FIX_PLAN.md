# 📋 Bot 交互系统修复计划

## 修复原则
1. **渐进式修复**：每次只修改一个模块，确保测试通过后再进行下一步
2. **兼容性保证**：修改不影响现有功能的正常使用
3. **可回滚性**：每步修改都要能独立回滚
4. **测试驱动**：先写测试，再修改代码

---

## 🔧 Step 1: 修复Admin回调Pattern冲突（HIGH-01）

### 问题描述
Admin模块的CallbackQueryHandler pattern过宽，可能捕获普通用户的回调，特别是`confirm_`前缀。

### 修改文件
- `src/bot_admin/handler.py`

### 具体修改

```python
# 原代码 (line 677):
pattern=r"^(admin_|price_|premium_edit_|energy_edit_|content_|settings_|edit_trx_rate|confirm_)"

# 修改为:
pattern=r"^(admin_|admin_price_|admin_premium_edit_|admin_energy_edit_|admin_content_|admin_settings_|admin_edit_trx_rate)$"
```

同时需要更新所有相关的callback_data:
- `price_premium` → `admin_price_premium`
- `price_trx_rate` → `admin_price_trx_rate`
- `price_energy` → `admin_price_energy`
- `premium_edit_3` → `admin_premium_edit_3`
- 等等...

### 测试方案

创建测试文件 `tests/test_admin_callback_fix.py`:

```python
import pytest
from unittest.mock import Mock, AsyncMock
from src.bot_admin.handler import AdminHandler

@pytest.mark.asyncio
async def test_admin_callback_pattern_not_catching_user_callbacks():
    """测试Admin模块不会捕获普通用户的confirm_payment回调"""
    handler = AdminHandler()
    
    # 测试普通用户的confirm_payment不被捕获
    update = Mock()
    update.callback_query.data = "confirm_payment"  # Premium模块的回调
    update.effective_user.id = 123456  # 非管理员
    
    # 这个回调不应该被Admin handler处理
    # 通过检查pattern是否匹配来验证
    import re
    pattern = r"^(admin_|admin_price_|admin_premium_edit_|admin_energy_edit_|admin_content_|admin_settings_|admin_edit_trx_rate)$"
    assert not re.match(pattern, "confirm_payment")
    
    # 测试Admin自己的回调仍能正常捕获
    assert re.match(pattern, "admin_price_premium")
    assert re.match(pattern, "admin_settings_timeout")
```

### 验证命令
```bash
# 运行Admin模块相关测试
pytest tests/test_admin_panel_integration.py -v
pytest tests/test_admin_callback_fix.py -v

# 运行所有测试确保没有破坏其他功能
pytest tests/ -v
```

### 回滚方案
如果出现问题，恢复 `src/bot_admin/handler.py` 到原始状态。

---

## 🔧 Step 2: 修复地址查询全局MessageHandler（HIGH-02）

### 问题描述
地址查询使用全局MessageHandler，可能拦截其他模块的文本输入。

### 修改文件
- `src/address_query/handler.py`
- `src/bot.py`

### 具体修改

1. **创建ConversationHandler** (`src/address_query/handler.py`):

```python
from telegram.ext import ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# 添加状态常量
AWAITING_ADDRESS = 1

class AddressQueryHandler:
    # ... 现有代码 ...
    
    @staticmethod
    def get_conversation_handler() -> ConversationHandler:
        """获取地址查询ConversationHandler"""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    AddressQueryHandler.start_query_conversation,
                    pattern=r"^menu_address_query$"
                ),
                MessageHandler(
                    filters.Regex(r"^🔍 地址查询$"),
                    AddressQueryHandler.start_query_conversation
                )
            ],
            states={
                AWAITING_ADDRESS: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        AddressQueryHandler.handle_address_input_in_conversation
                    )
                ]
            },
            fallbacks=[
                CallbackQueryHandler(
                    AddressQueryHandler.cancel_conversation,
                    pattern=r"^(cancel_query|back_to_main)$"
                ),
                CommandHandler("cancel", AddressQueryHandler.cancel_conversation)
            ],
            name="address_query",
            persistent=False,
            allow_reentry=True
        )
    
    @staticmethod
    async def start_query_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始地址查询对话"""
        # 原query_address的逻辑，但返回AWAITING_ADDRESS
        # ... 现有代码 ...
        return AWAITING_ADDRESS
    
    @staticmethod
    async def handle_address_input_in_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """在对话中处理地址输入"""
        # 原handle_address_input的逻辑，但返回ConversationHandler.END
        # ... 现有代码 ...
        return ConversationHandler.END
    
    @staticmethod
    async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消对话"""
        # ... 清理逻辑 ...
        return ConversationHandler.END
```

2. **更新bot.py注册**:

```python
# 删除原有的全局MessageHandler (lines 142-156)
# 替换为:
from src.address_query.handler import AddressQueryHandler

# 在handler注册部分添加
self.app.add_handler(AddressQueryHandler.get_conversation_handler())
```

### 测试方案

创建测试文件 `tests/test_address_query_conversation.py`:

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram.ext import ConversationHandler
from src.address_query.handler import AddressQueryHandler, AWAITING_ADDRESS

@pytest.mark.asyncio
async def test_address_query_only_in_conversation():
    """测试地址查询只在对话流程中处理文本"""
    update = Mock()
    context = Mock()
    context.user_data = {}
    
    # 测试未进入对话时，不处理随机文本
    update.message.text = "Hello World"
    # 不在对话中，应该返回None或不处理
    
    # 测试进入对话后，处理地址
    result = await AddressQueryHandler.start_query_conversation(update, context)
    assert result == AWAITING_ADDRESS
    
    # 现在应该能处理地址输入
    update.message.text = "TTestAddress123456789012345678901234"
    result = await AddressQueryHandler.handle_address_input_in_conversation(update, context)
    assert result == ConversationHandler.END

@pytest.mark.asyncio
async def test_address_query_not_interfering_with_other_modules():
    """测试地址查询不干扰其他模块的文本输入"""
    # 模拟在Premium模块输入收件人时
    # 地址查询handler不应该被触发
    pass  # 具体实现根据实际测试需求
```

### 验证命令
```bash
# 运行地址查询相关测试
pytest tests/test_address_query_rate_limit.py -v
pytest tests/test_address_validator.py -v
pytest tests/test_address_query_conversation.py -v

# 确保其他模块没有受影响
pytest tests/test_premium_order.py -v
pytest tests/test_wallet.py -v
```

---

## 🔧 Step 3: 统一权限检查机制（MEDIUM-01）

### 问题描述
不同管理员功能使用不同的权限检查方式。

### 修改文件
- `src/health.py`
- `src/orders/query_handler.py`
- `src/bot_admin/middleware.py`

### 具体修改

1. **修改health.py使用装饰器**:

```python
from src.bot_admin.middleware import owner_only

@owner_only
async def health_command(update, context):
    """健康检查命令"""
    # 删除原有的手动权限检查 (lines 96-98)
    # 直接执行健康检查逻辑
    health_status = await health_service.check_health()
    # ...
```

2. **确保orders模块正确导入装饰器**:

```python
# src/orders/query_handler.py
from src.bot_admin.middleware import owner_only

@owner_only
async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ...
```

### 测试方案

```python
# tests/test_unified_permissions.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.health import health_command
from src.orders.query_handler import orders_command

@pytest.mark.asyncio
async def test_admin_commands_require_owner():
    """测试所有管理员命令都需要owner权限"""
    # 模拟非owner用户
    update = Mock()
    update.effective_user.id = 999999
    context = Mock()
    
    # health命令应该拒绝
    result = await health_command(update, context)
    # 验证返回了权限错误消息
    
    # orders命令应该拒绝
    result = await orders_command(update, context)
    # 验证返回了权限错误消息
```

### 验证命令
```bash
pytest tests/test_health.py -v
pytest tests/test_orders_query_handler.py -v
pytest tests/test_unified_permissions.py -v
```

---

## 🔧 Step 4: 创建常量管理文件（MEDIUM-02）

### 创建文件
`src/constants.py`

### 内容

```python
"""
Bot常量定义
"""

# 底部键盘按钮文字（Reply Keyboard）
BUTTON_PREMIUM = "💎 Premium会员"
BUTTON_ENERGY = "⚡ 能量兑换"
BUTTON_ADDRESS = "🔍 地址查询"
BUTTON_PROFILE = "👤 个人中心"
BUTTON_TRX = "🔄 TRX 兑换"
BUTTON_SUPPORT = "👨‍💼 联系客服"
BUTTON_RATES = "💵 实时U价"
BUTTON_CLONE = "🎁 免费克隆"

# 底部键盘布局
REPLY_KEYBOARD_BUTTONS = [
    [BUTTON_PREMIUM, BUTTON_ENERGY],
    [BUTTON_ADDRESS, BUTTON_PROFILE],
    [BUTTON_TRX, BUTTON_SUPPORT],
    [BUTTON_RATES, BUTTON_CLONE],
]

# Inline按钮回调数据
CALLBACK_MENU_PREMIUM = "menu_premium"
CALLBACK_MENU_ENERGY = "menu_energy"
CALLBACK_MENU_ADDRESS = "menu_address_query"
CALLBACK_MENU_PROFILE = "menu_profile"
CALLBACK_MENU_CLONE = "menu_clone"
CALLBACK_MENU_SUPPORT = "menu_support"
CALLBACK_MENU_RATES_ALL = "menu_rates_all"
CALLBACK_BACK_TO_MAIN = "back_to_main"

# ConversationHandler状态
# Premium
PREMIUM_SELECTING_PACKAGE = 1
PREMIUM_ENTERING_RECIPIENTS = 2
PREMIUM_CONFIRMING_PAYMENT = 3

# 地址查询
ADDRESS_AWAITING_INPUT = 1

# TRX兑换
TRX_INPUT_AMOUNT = 1
TRX_INPUT_ADDRESS = 2
TRX_CONFIRM_PAYMENT = 3
TRX_INPUT_TX_HASH = 4

# 能量
ENERGY_SELECT_TYPE = 1
ENERGY_SELECT_PACKAGE = 2
ENERGY_INPUT_COUNT = 3
ENERGY_INPUT_ADDRESS = 4
ENERGY_SHOW_PAYMENT = 5
ENERGY_INPUT_TX_HASH = 6

# 超时设置（秒）
CONVERSATION_TIMEOUT = 600  # 10分钟
```

### 更新代码使用常量

```python
# src/menu/main_menu.py
from src.constants import (
    REPLY_KEYBOARD_BUTTONS,
    BUTTON_PREMIUM, BUTTON_ENERGY, # ...
)

@staticmethod
def _build_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        REPLY_KEYBOARD_BUTTONS,
        resize_keyboard=True,
        one_time_keyboard=False,
    )

# src/bot.py
from src.constants import (
    BUTTON_ADDRESS, BUTTON_PROFILE, BUTTON_SUPPORT,
    BUTTON_RATES, BUTTON_CLONE
)

keyboard_buttons = [
    BUTTON_ADDRESS, BUTTON_PROFILE, BUTTON_SUPPORT,
    BUTTON_RATES, BUTTON_CLONE
]
```

### 测试方案

```python
# tests/test_constants.py
from src.constants import *

def test_button_count():
    """测试按钮数量正确"""
    assert len(REPLY_KEYBOARD_BUTTONS) == 4  # 4行
    assert len(REPLY_KEYBOARD_BUTTONS[0]) == 2  # 每行2个
    
def test_button_uniqueness():
    """测试按钮文字唯一性"""
    all_buttons = []
    for row in REPLY_KEYBOARD_BUTTONS:
        all_buttons.extend(row)
    assert len(all_buttons) == len(set(all_buttons))
```

### 验证命令
```bash
pytest tests/test_constants.py -v
pytest tests/test_welcome_menu.py -v
```

---

## 🔧 Step 5: 添加ConversationHandler超时（MEDIUM-03）

### 修改文件
- `src/premium/handler.py`
- `src/trx_exchange/handler.py`
- `src/energy/handler_direct.py`
- `src/wallet/profile_handler.py`

### 具体修改

```python
# src/premium/handler.py
from src.constants import CONVERSATION_TIMEOUT

def get_conversation_handler(self) -> ConversationHandler:
    return ConversationHandler(
        # ... 现有配置 ...
        conversation_timeout=CONVERSATION_TIMEOUT,  # 添加超时
        name="premium_handler",
        persistent=False,
        allow_reentry=True
    )

# 类似地更新其他模块
```

### 添加超时处理

```python
async def conversation_timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理对话超时"""
    await update.message.reply_text(
        "⏰ 操作超时，已自动取消。\n"
        "如需继续，请重新开始。",
        reply_markup=MainMenuHandler._build_reply_keyboard()
    )
    return ConversationHandler.END
```

### 测试方案

```python
# tests/test_conversation_timeout.py
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_conversation_timeout():
    """测试ConversationHandler超时机制"""
    from src.premium.handler import PremiumHandler
    
    handler = PremiumHandler(
        order_manager=Mock(),
        suffix_manager=Mock(),
        delivery_service=Mock(),
        receive_address="TTest123"
    )
    
    conv_handler = handler.get_conversation_handler()
    assert conv_handler.conversation_timeout == 600  # 10分钟
```

### 验证命令
```bash
pytest tests/test_conversation_timeout.py -v
pytest tests/test_premium_order.py -v
pytest tests/test_trx_exchange.py -v
```

---

## 🔧 Step 6: 统一文案和清理代码（LOW）

### 修改内容
1. 统一所有"Premium会员"文案（不使用"飞机会员"）
2. 统一"地址查询"文案（不使用"地址监听"）
3. 删除无用的注释和调试代码

### 批量替换脚本

```python
# scripts/unify_text.py
import os
import re
from pathlib import Path

replacements = {
    "飞机会员": "Premium会员",
    "地址监听": "地址查询",
    "实时U价": "实时U价",  # 保持一致
}

def replace_in_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {filepath}")

# 扫描所有Python文件
root = Path(".")
for file in root.rglob("*.py"):
    if "venv" not in str(file) and "__pycache__" not in str(file):
        replace_in_file(file, replacements)
```

### 验证命令
```bash
python scripts/unify_text.py
pytest tests/ -v  # 确保所有测试仍然通过
```

---

## 🔧 Step 7: 添加集成测试套件

### 创建文件
`tests/test_button_integration.py`

### 内容

```python
"""
按钮交互集成测试
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, CallbackQuery, Message, User
from telegram.ext import ContextTypes

class TestButtonIntegration:
    """测试所有按钮的完整交互流程"""
    
    @pytest.fixture
    def mock_update(self):
        """创建模拟的Update对象"""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        update.effective_user.first_name = "Test"
        return update
    
    @pytest.fixture
    def mock_context(self):
        """创建模拟的Context对象"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
    @pytest.mark.asyncio
    async def test_main_menu_all_buttons_have_handlers(self, mock_update, mock_context):
        """测试主菜单所有按钮都有对应的处理器"""
        from src.constants import REPLY_KEYBOARD_BUTTONS
        from src.bot import Bot
        
        bot = Bot()
        
        # 测试每个按钮都能找到对应的handler
        for row in REPLY_KEYBOARD_BUTTONS:
            for button_text in row:
                # 模拟按钮点击
                mock_update.message = Mock(spec=Message)
                mock_update.message.text = button_text
                
                # 验证有handler能处理这个按钮
                # 这里需要根据实际的handler注册情况来验证
                
    @pytest.mark.asyncio
    async def test_conversation_flow_premium(self, mock_update, mock_context):
        """测试Premium购买完整流程"""
        from src.premium.handler import PremiumHandler
        
        # 模拟完整的购买流程
        # 1. 点击Premium按钮
        # 2. 选择套餐
        # 3. 输入收件人
        # 4. 确认支付
        pass
    
    @pytest.mark.asyncio
    async def test_no_callback_conflicts(self):
        """测试没有回调冲突"""
        from src.constants import (
            CALLBACK_MENU_PREMIUM,
            CALLBACK_MENU_ENERGY,
            CALLBACK_MENU_ADDRESS,
            CALLBACK_MENU_PROFILE,
        )
        
        # 收集所有callback_data
        all_callbacks = [
            CALLBACK_MENU_PREMIUM,
            CALLBACK_MENU_ENERGY,
            CALLBACK_MENU_ADDRESS,
            CALLBACK_MENU_PROFILE,
            # ... 添加所有callback
        ]
        
        # 确保没有重复
        assert len(all_callbacks) == len(set(all_callbacks))
        
        # 确保admin回调不会与用户回调冲突
        admin_callbacks = [
            "admin_stats",
            "admin_prices",
            "admin_content",
            # ...
        ]
        
        user_callbacks = [
            "confirm_payment",  # Premium的
            "profile_deposit",  # 个人中心的
            # ...
        ]
        
        # 确保没有交集
        assert not set(admin_callbacks) & set(user_callbacks)
```

### 运行完整测试套件

```bash
# 创建测试脚本
cat > scripts/run_full_test.sh << 'EOF'
#!/bin/bash
echo "========================================"
echo "运行完整测试套件"
echo "========================================"

# 清理缓存
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null

# 运行测试
echo "1. 测试核心功能..."
pytest tests/test_amount_calculator.py -v
pytest tests/test_payment_processor.py -v
pytest tests/test_recipient_parser.py -v

echo "2. 测试权限系统..."
pytest tests/test_admin_panel_integration.py -v
pytest tests/test_unified_permissions.py -v

echo "3. 测试按钮交互..."
pytest tests/test_button_integration.py -v
pytest tests/test_bot_functionality.py -v

echo "4. 测试对话流程..."
pytest tests/test_premium_order.py -v
pytest tests/test_trx_exchange.py -v
pytest tests/test_energy_direct.py -v
pytest tests/test_address_query_conversation.py -v

echo "5. 测试数据库功能..."
pytest tests/test_wallet.py -v
pytest tests/test_deposit_callback.py -v

echo "6. 运行所有测试..."
pytest tests/ -v --tb=short

echo "========================================"
echo "测试完成！"
echo "========================================"
EOF

chmod +x scripts/run_full_test.sh
```

---

## 📊 验证清单

每完成一个步骤后，使用以下清单验证：

### Step 1 验证 ✅
- [ ] Admin回调不再捕获用户的confirm_payment
- [ ] Admin功能正常工作
- [ ] 测试：`pytest tests/test_admin_* -v`

### Step 2 验证 ✅
- [ ] 地址查询只在自己的对话中处理文本
- [ ] 其他模块的文本输入不受影响
- [ ] 测试：`pytest tests/test_address_* -v`

### Step 3 验证 ✅
- [ ] 所有管理员命令使用统一的权限检查
- [ ] 非管理员无法访问管理功能
- [ ] 测试：`pytest tests/test_*permissions* -v`

### Step 4 验证 ✅
- [ ] 所有按钮文字使用常量
- [ ] 按钮布局正确（4x2）
- [ ] 测试：`pytest tests/test_constants.py -v`

### Step 5 验证 ✅
- [ ] ConversationHandler有超时设置
- [ ] 超时后正确清理状态
- [ ] 测试：`pytest tests/test_*timeout* -v`

### Step 6 验证 ✅
- [ ] 文案统一一致
- [ ] 无冗余代码
- [ ] 测试：`pytest tests/ -v`

### Step 7 验证 ✅
- [ ] 集成测试覆盖所有按钮
- [ ] 无回调冲突
- [ ] 完整流程测试通过
- [ ] 测试：`./scripts/run_full_test.sh`

---

## 🚀 执行步骤

```bash
# 1. 创建修复分支
git checkout -b fix/button-interactions

# 2. 按顺序执行每个步骤
# Step 1
# ... 修改代码 ...
pytest tests/test_admin_* -v
git add -A && git commit -m "fix: 修复Admin回调Pattern冲突"

# Step 2
# ... 修改代码 ...
pytest tests/test_address_* -v
git add -A && git commit -m "fix: 地址查询改为ConversationHandler"

# ... 继续其他步骤 ...

# 最后运行完整测试
./scripts/run_full_test.sh

# 如果全部通过，合并到主分支
git checkout main
git merge fix/button-interactions
```
