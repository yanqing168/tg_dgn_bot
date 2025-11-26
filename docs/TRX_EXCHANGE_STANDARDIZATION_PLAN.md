# 🔄 TRX兑换模块标准化实施计划

**开始时间**: 2025-11-26 05:34  
**目标**: 将TRX兑换模块标准化，使用SafeConversationHandler和NavigationManager

---

## 📊 现有模块分析

### 当前结构 (src/trx_exchange/)
```
trx_exchange/
├── __init__.py
├── handler.py          # 主处理器（需要标准化）
├── config.py           # 配置（保留）
├── models.py           # 数据模型（保留）
├── rate_manager.py     # 汇率管理（保留）
└── trx_sender.py       # TRX发送器（保留）
```

### 功能分析
1. **TRX兑换流程**: USDT → TRX
2. **最低兑换**: 5 USDT
3. **最高兑换**: 20,000 USDT
4. **到账时间**: 5-10分钟
5. **手续费**: Bot承担

### 状态流程
```
START → INPUT_AMOUNT → INPUT_ADDRESS → SHOW_PAYMENT → CONFIRM_PAYMENT → INPUT_TX_HASH → END
```

---

## 🎯 标准化目标

### 新模块结构 (src/modules/trx_exchange/)
```
modules/trx_exchange/
├── __init__.py         # 模块导出
├── handler.py          # 标准化处理器（继承BaseModule）
├── messages.py         # HTML消息模板
├── states.py           # 状态常量
└── keyboards.py        # 键盘布局
```

### 保留的工具类
- `src/trx_exchange/config.py` - 配置管理
- `src/trx_exchange/models.py` - 数据模型
- `src/trx_exchange/rate_manager.py` - 汇率管理
- `src/trx_exchange/trx_sender.py` - TRX发送器

---

## 📋 实施步骤

### 步骤1: 创建states.py ✅
定义所有对话状态常量

### 步骤2: 创建messages.py ✅
将所有消息转换为HTML格式

### 步骤3: 创建keyboards.py ✅
提取所有键盘布局

### 步骤4: 创建handler.py ✅
- 继承BaseModule
- 使用SafeConversationHandler
- 使用NavigationManager
- 保持原有业务逻辑

### 步骤5: 创建__init__.py ✅
导出TRXExchangeModule

### 步骤6: 编写测试 ✅
创建test_trx_exchange_standard.py

### 步骤7: 集成到bot_v2.py ✅
注册新模块

### 步骤8: 测试验证 ✅
- 单元测试
- 按钮交互测试

---

## 🔧 关键修改点

### 1. 使用SafeConversationHandler
```python
from src.common.conversation_wrapper import SafeConversationHandler

conv_handler = SafeConversationHandler.create(
    entry_points=[...],
    states={...},
    fallbacks=[...],
    name="trx_exchange_conversation"
)
```

### 2. 使用NavigationManager
```python
from src.common.navigation_manager import NavigationManager

async def cancel(self, update, context):
    return await NavigationManager.cleanup_and_show_main_menu(update, context)
```

### 3. HTML消息格式
```python
# 旧格式（Markdown）
"🔄 *TRX 闪兑*\n\n24小时自动兑换"

# 新格式（HTML）
"🔄 <b>TRX 闪兑</b>\n\n24小时自动兑换"
```

### 4. 状态管理
```python
# 直接使用context.user_data
context.user_data["usdt_amount"] = amount
context.user_data["receive_address"] = address
```

---

## ⚠️ 注意事项

1. **保留业务逻辑**: 不改变TRX发送、汇率计算等核心逻辑
2. **保留工具类**: rate_manager、trx_sender等保持不变
3. **向后兼容**: 旧模块保留，新旧并存
4. **测试覆盖**: 确保所有功能测试通过

---

## 📊 预期效果

- ✅ 统一的对话处理
- ✅ 统一的导航管理
- ✅ 统一的错误处理
- ✅ 更好的代码组织
- ✅ 完整的测试覆盖

---

**状态**: 准备开始实施
