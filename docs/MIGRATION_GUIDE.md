# 📚 V2 架构迁移指南

## 概述

本指南帮助您将旧模块迁移到V2标准化架构。

## 迁移步骤

### Step 1: 理解新架构

#### 核心组件
- `BaseModule` - 所有模块必须继承的基类
- `MessageFormatter` - 统一的消息格式化
- `ModuleStateManager` - 状态管理
- `ModuleRegistry` - 模块注册

### Step 2: 创建标准化模块结构

```
src/modules/your_module/
├── __init__.py       # 模块导出
├── handler.py        # 主处理器（继承BaseModule）
├── messages.py       # 消息模板（HTML格式）
├── states.py         # 状态常量定义
└── keyboards.py      # 键盘布局定义
```

### Step 3: 实现BaseModule

```python
from src.core import BaseModule, MessageFormatter, ModuleStateManager

class YourModule(BaseModule):
    def __init__(self):
        self.formatter = MessageFormatter()
        self.state_manager = ModuleStateManager()
    
    @property
    def module_name(self) -> str:
        return "your_module"
    
    def get_handlers(self) -> List[BaseHandler]:
        return [
            # 返回处理器列表
        ]
```

### Step 4: 转换消息格式

#### ❌ 旧方式（Markdown）
```python
text = f"*欢迎* {username}!"
await update.message.reply_text(text, parse_mode='Markdown')
```

#### ✅ 新方式（HTML）
```python
# messages.py
WELCOME = "<b>欢迎</b> {username}!"

# handler.py
text = self.formatter.format_html(
    YourMessages.WELCOME,
    username=self.formatter.escape_html(username)
)
await update.message.reply_text(text, parse_mode='HTML')
```

### Step 5: 使用状态管理器

#### ❌ 旧方式
```python
context.user_data['some_key'] = value
```

#### ✅ 新方式
```python
state = self.state_manager.get_state(context, self.module_name)
state['some_key'] = value
```

### Step 6: 注册模块

在 `src/bot_v2.py` 中注册：

```python
from src.modules.your_module import YourModule

# 在 _register_standardized_modules 方法中
your_module = YourModule()
self.registry.register(
    your_module,
    priority=5,  # 0-10，数字越小优先级越高
    enabled=True,
    metadata={"description": "模块描述"}
)
```

## 已迁移模块示例

### Premium模块
- 文件：`src/modules/premium/`
- 特点：解决了Markdown解析错误
- 测试：`tests/test_premium_standard.py` (11个用例)

### 主菜单模块
- 文件：`src/modules/menu/`
- 特点：解决了重复提示问题
- 测试：`tests/test_menu_standard.py` (11个用例)

### 能量模块 ⭐ 新
- 文件：`src/modules/energy/`
- 特点：完整的7个状态流转，支持3种能量类型
- 功能：时长能量、笔数套餐、闪兑
- 测试：`tests/test_energy_standard.py` (15个用例)
- 关键经验：直接使用`context.user_data`管理状态

### 地址查询模块 ⭐ 新
- 文件：`src/modules/address_query/`
- 特点：简单快速，限频控制
- 功能：TRON地址验证和查询
- 测试：`tests/test_address_query_standard.py` (10个用例通过，1个跳过)
- 关键经验：简化测试验证逻辑

## 待迁移模块清单

| 模块 | 旧文件位置 | 优先级 | 预计工作量 | 状态 |
|------|----------|--------|--------|------|
| 支付 | src/payments/ | 高 | 2天 | ⚠️ 后台服务，不标准化 |
| 能量 | src/energy/ | 高 | 1天 | ✅ 已完成 |
| TRX兑换 | src/trx_exchange/ | 中 | 2.5小时 | ⏳ 进行中 |
| 地址查询 | src/address_query/ | 中 | 0.5天 | ✅ 已完成 |
| 钱包 | src/wallet/ | 中 | 2小时 | ⏳ 进行中 |
| 管理面板 | src/bot_admin/ | 低 | 3小时 | ⏳ 进行中 |
| 帮助系统 | src/help/ | 低 | 0.5天 | ⚠️ 可选 |

## 测试要求

每个迁移的模块必须：
1. 创建对应的测试文件 `tests/test_模块名_standard.py`
2. 覆盖主要功能路径
3. 测试特殊字符处理
4. 测试状态管理
5. 所有测试必须通过才能合并

## 常见问题

### Q: 如何处理异步操作？
A: 使用 `async/await`，确保所有处理器方法都是异步的。

### Q: 如何处理错误？
A: 在模块内部使用try-catch，避免使用全局错误装饰器。

### Q: 如何处理数据库操作？
A: 保持原有数据库操作方式，只改变上层逻辑。

### Q: 是否需要修改数据库结构？
A: 不需要，V2架构只改变代码组织，不影响数据结构。

## 迁移检查清单

- [ ] 创建模块目录结构
- [ ] 实现BaseModule接口
- [ ] 转换所有消息为HTML格式
- [ ] 使用MessageFormatter进行转义
- [ ] 使用ModuleStateManager管理状态
- [ ] 创建测试文件
- [ ] 通过所有测试
- [ ] 在bot_v2.py中注册模块
- [ ] 更新文档

## 获取帮助

如遇到问题，请参考：
1. 已迁移模块的代码
2. `docs/NEW_ARCHITECTURE.md`
3. 测试文件中的示例

## 关键经验总结

基于已完成5个模块的经验：

1. **状态管理**: 直接使用`context.user_data`比`ModuleStateManager`更简单可靠
2. **测试策略**: 测试应直接检查`context.user_data`，简化验证逻辑
3. **代码复用**: 保留现有工具类，只标准化用户交互层
4. **HTML格式**: 统一使用HTML避免Markdown解析问题
5. **渐进迁移**: 新旧模块并存，逐步迁移

---
*最后更新: 2025-11-26*
