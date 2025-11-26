# Bot 菜单和引流按钮功能说明

## 功能概述

实现了两个重要的用户体验功能：

1. **Bot 左下角菜单按钮**：快速访问常用命令

2. **可配置引流按钮**：欢迎语下方的自定义按钮，支持内部功能和外部链接

## 1. Bot 菜单命令

### 📱 效果展示

默认情况下，所有用户在左下角「☰ 菜单」中只会看到一个命令：

```text
🏠 开始使用 / 主菜单    /start

```

当 Bot Owner（`settings.bot_owner_id`）使用同一个 Bot 时，会额外看到管理员命令：

```text
🏠 开始使用 / 主菜单    /start
🏥 系统健康检查        /health
🔐 管理员面板          /admin
📦 订单查询管理        /orders

```

### 实现方式

**代码位置**: `src/bot.py`

```python
async def setup_bot_commands(self):
    """设置 Bot 菜单命令（左下角菜单按钮）"""
    from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

    # 1. 所有用户：仅展示 /start
    common_commands = [
        BotCommand("start", "🏠 开始使用 / 主菜单"),
    ]
    await self.app.bot.set_my_commands(
        common_commands,
        scope=BotCommandScopeDefault()
    )

    # 2. Owner：额外的管理员命令
    if settings.bot_owner_id and settings.bot_owner_id > 0:
        admin_commands = [
            BotCommand("start", "🏠 开始使用 / 主菜单"),
            BotCommand("health", "🏥 系统健康检查"),
            BotCommand("admin", "🔐 管理员面板"),
            BotCommand("orders", "📦 订单查询管理"),
        ]
        await self.app.bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=settings.bot_owner_id)
        )

```text

### 特点

- ✅ Bot 启动时自动设置

- ✅ 所有用户可见

- ✅ 支持 emoji 图标

- ✅ 提供快捷操作入口

### 修改方法

编辑 `src/bot.py` 中的 `setup_bot_commands()` 方法：

```python
commands = [
    BotCommand("your_command", "📌 你的说明"),
    # 添加更多命令...

]

```text

## 2. 可配置引流按钮

### 效果展示

用户发送 `/start` 命令后，欢迎语下方显示自定义按钮。默认布局为 3 行、每行 2 个 inline 按钮：

```text
┌─────────────────────────────────────┐
│  💎 开通会员  │  💰 查看价格        │
├─────────────────────────────────────┤
│  ⚡ 能量兑换   │  🔍 地址查询        │
├─────────────────────────────────────┤
│  🎁 免费克隆  │  👨‍💼 联系客服     │
└─────────────────────────────────────┘

```text

### 📋 默认配置

**欢迎语** (`welcome_message`):

```text
👋 欢迎使用 TG DGN Bot！

🤖 你的 Telegram 数字服务助手

我们提供以下服务：
💎 Premium 会员直充
⚡ TRON 能量兑换
🔍 波场地址查询
🎁 免费克隆服务
💰 USDT 余额管理

请选择下方功能开始使用 👇

```text

**按钮配置** (`promotion_buttons`，代码位于 `src/config.py`):

```json
[
  {"text": "💎 开通会员", "callback": "menu_premium"},
  {"text": "💰 查看价格", "callback": "menu_profile"}
],
[
  {"text": "⚡ 能量兑换", "callback": "menu_energy"},
  {"text": "🔍 地址查询", "callback": "menu_address_query"}
],
[
  {"text": "🎁 免费克隆", "callback": "menu_clone"},
  {"text": "👨‍💼 联系客服", "callback": "menu_support"}
]

```text

### 🔄 TRX 兑换入口（Reply + Inline 保持一致）

- 底部 Reply 键盘文字：`🔄 TRX 兑换`
- Inline 引流按钮回调：`menu_trx_exchange`
- 实际业务处理：`src/trx_exchange/handler.py` 中的 `TRXExchangeHandler`
- ConversationHandler 入口：
  - `MessageHandler(filters.Regex("^🔄 TRX 兑换$"), start_exchange)`
  - `CallbackQueryHandler(start_exchange, pattern="^menu_trx_exchange$")`

> 这样可确保任意入口都会进入同一个兑换流程（输入金额 → 输入地址 → 支付引导），不会影响其他按钮或管理员面板逻辑。

## 配置方式

### 方式一：使用默认配置（推荐）

无需任何操作，开箱即用。默认配置已在 `src/config.py` 中定义。

### 方式二：环境变量自定义

在 `.env` 文件中添加：

#### 自定义欢迎语

```bash
WELCOME_MESSAGE="👋 欢迎 {first_name}！\n\n您的自定义欢迎语内容...\n\n点击下方按钮开始"

```text

**说明**:

- 支持 HTML 标签：`<b>`、`<i>`、`<u>`、`<code>` 等

- `{first_name}` 会被替换为用户的名字

- 使用 `\n` 表示换行

#### 自定义引流按钮

```bash
PROMOTION_BUTTONS='[{"text": "💎 开会员", "callback": "menu_premium"}, {"text": "💰 价格", "url": "https://example.com"}],[{"text": "📱 关注频道", "url": "https://t.me/yourchannel"}]'

```text

**按钮类型**:

1. **回调按钮** (内部功能):

   ```json
   {"text": "按钮文字", "callback": "callback_data"}
   ```

   点击后触发 Bot 内部功能（如打开菜单、启动对话流程）

1. **链接按钮** (外部跳转):

   ```json
   {"text": "按钮文字", "url": "https://example.com"}
   ```

   点击后在浏览器中打开外部链接

**布局规则**:

- 每行最多 2 个按钮

- 用逗号分隔按钮

- 用 `],[` 分隔行

### 方式三：修改代码默认值

编辑 `src/config.py`:

```python
welcome_message: str = (
    "您的自定义欢迎语..."
)

promotion_buttons: str = (
    '[{"text": "按钮1", "callback": "data1"},'
    '{"text": "按钮2", "url": "https://link.com"}]'
)

```text

## 技术实现

### 核心代码

**配置定义** (`src/config.py`):

```python
class Settings(BaseSettings):
    welcome_message: str = "..."
    promotion_buttons: str = "..."

```text

**按钮构建** (`src/menu/main_menu.py`):

```python
@staticmethod
def _build_promotion_buttons():
    """构建引流按钮（从配置读取）"""
    from ..config import settings

    try:
        buttons_config = settings.promotion_buttons
        button_rows = eval(f'[{buttons_config}]')

        keyboard = []
        for row in button_rows:
            button_row = []
            for btn in row:
                text = btn.get('text', '')
                url = btn.get('url')
                callback = btn.get('callback')

                if url:
                    button_row.append(InlineKeyboardButton(text, url=url))
                elif callback:
                    button_row.append(InlineKeyboardButton(text, callback_data=callback))

            if button_row:
                keyboard.append(button_row)

        return keyboard
    except Exception as e:
        logger.error(f"解析引流按钮配置失败: {e}")
        return [...]  # 返回默认按钮

```text

**菜单命令设置** (`src/bot.py`):

```python
async def setup_bot_commands(self):
    """设置 Bot 菜单命令"""
    commands = [...]
    await self.app.bot.set_my_commands(commands)

```text

## 使用场景

### 场景 1：引流到外部资源

```bash
PROMOTION_BUTTONS='[{"text": "📱 关注频道", "url": "https://t.me/yourchannel"}, {"text": "🌐 访问网站", "url": "https://yoursite.com"}]'

```text

### 场景 2：突出主要功能

```bash
PROMOTION_BUTTONS='[{"text": "🔥 热门功能", "callback": "menu_premium"}],[{"text": "🆓 免费试用", "callback": "menu_clone"}]'

```text

### 场景 3：混合内外链接

```bash
PROMOTION_BUTTONS='[{"text": "💎 购买会员", "callback": "menu_premium"}, {"text": "📖 使用教程", "url": "https://docs.example.com"}],[{"text": "👥 加入群组", "url": "https://t.me/yourgroup"}]'

```text

## 测试验证

运行测试：

```bash
pytest tests/test_welcome_menu.py -v

```text

预期结果：

```text
✅ test_welcome_message_exists PASSED
✅ test_welcome_message_contains_welcome_text PASSED
✅ test_promotion_buttons_config_exists PASSED
✅ test_promotion_buttons_format PASSED
✅ test_build_promotion_buttons PASSED
✅ test_promotion_buttons_contain_callbacks PASSED
✅ test_promotion_buttons_text_not_empty PASSED
✅ test_welcome_message_length PASSED
✅ test_promotion_buttons_default_values PASSED

9 passed in 0.35s

```text

## 常见问题

### Q: 如何添加更多按钮？

A: 在配置中添加新的行，注意每行最多 2 个按钮：

```bash
PROMOTION_BUTTONS='[{"text": "按钮1", "callback": "data1"}],[{"text": "按钮2", "callback": "data2"}],[{"text": "按钮3", "callback": "data3"}]'

```text

### Q: 按钮可以只有一个吗？

A: 可以，每行可以 1-2 个按钮：

```bash
PROMOTION_BUTTONS='[{"text": "唯一按钮", "callback": "data"}]'

```text

### Q: 如何添加外部链接？

A: 使用 `url` 而不是 `callback`：

```json
{"text": "访问网站", "url": "https://example.com"}

```text

### Q: 欢迎语支持图片吗？

A: 当前版本仅支持文本和 HTML 格式，不支持图片。

### Q: 配置格式错误会怎样？

A: 如果配置解析失败，会自动回退到默认按钮配置，并在日志中记录错误。

### Q: 菜单命令何时生效？

A: Bot 启动时自动设置，立即生效。

### Q: 可以为不同用户显示不同按钮吗？

A: 当前版本所有用户看到相同按钮。如需差异化，需要在代码中添加用户判断逻辑。

### Q: 按钮点击后会发生什么？

A:

- `callback` 按钮：触发 Bot 内部功能（如打开菜单、开始对话）

- `url` 按钮：在浏览器中打开外部链接

## 配置示例

### 示例 1：简洁版

```bash
WELCOME_MESSAGE="👋 欢迎！\n\n选择功能开始使用："
PROMOTION_BUTTONS='[{"text": "开始", "callback": "menu_premium"}]'

```text

### 示例 2：营销版

```bash
WELCOME_MESSAGE="🎉 限时优惠！\n\n立即购买 Premium 会员\n享受 8 折优惠！"
PROMOTION_BUTTONS='[{"text": "💎 立即购买", "callback": "menu_premium"}],[{"text": "📱 关注频道", "url": "https://t.me/yourchannel"}, {"text": "👥 加入群组", "url": "https://t.me/yourgroup"}]'

```text

### 示例 3：功能导航版（当前默认）

```bash
WELCOME_MESSAGE="👋 欢迎使用 TG DGN Bot！\n\n🤖 你的 Telegram 数字服务助手"
PROMOTION_BUTTONS='[{"text": "💎 开通会员", "callback": "menu_premium"}, {"text": "💰 查看价格", "callback": "menu_profile"}],[{"text": "⚡ 能量兑换", "callback": "menu_energy"}, {"text": "🔍 地址查询", "callback": "menu_address_query"}],[{"text": "🎁 免费克隆", "callback": "menu_clone"}, {"text": "👨‍💼 联系客服", "callback": "menu_support"}]'

```text

## 最佳实践

### ✅ 推荐做法

1. **简洁明了**：按钮文字不超过 10 个字

2. **使用 emoji**：增加视觉吸引力

3. **重点突出**：最重要的功能放在第一行

4. **合理布局**：每行 1-2 个按钮，不超过 4 行

5. **测试验证**：修改后运行测试确保格式正确

### ❌ 避免做法

1. 按钮过多（超过 8 个）

2. 文字过长（影响显示）

3. 全部外链（失去 Bot 功能性）

4. JSON 格式错误（导致回退默认配置）

## 未来扩展

### 🔮 可能的增强

- 🌍 多语言支持（根据用户语言显示不同内容）

- 👤 个性化按钮（VIP 用户看到不同选项）

- 📊 点击统计（分析用户偏好）

- 🎨 主题切换（不同风格的按钮样式）

- 🖼️ 图片欢迎语（支持发送图片 + 按钮）

## 总结

✅ **Bot 菜单命令**

- 左下角快捷入口

- 5 个常用命令

- 启动时自动设置

✅ **可配置引流按钮**

- 支持内部功能和外部链接

- 灵活的 JSON 配置

- 每行 1-2 个按钮

- 错误自动回退

✅ **易于使用**

- 默认配置开箱即用

- 环境变量灵活定制

- 完整测试覆盖

---

**文档版本**: 1.0
**最后更新**: 2025-10-28
**维护者**: TG DGN Bot Team
