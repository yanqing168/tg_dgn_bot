# 按钮 & 命令地图（an_luoji）

## 1. 功能概览

| 模块 | Section 名称 | 入口类型 | 角色 |
| --- | --- | --- | --- |
| 主菜单 | 主菜单/推广面板 | /start、Reply 键盘、Inline 菜单 | 全体 @src/menu/main_menu.py#82-205 |
| Premium | Premium 会员直充 | /premium、Reply、Inline | 全体，Conversation `premium_handler` @src/premium/handler.py#66-90 |
| Energy | 能量直转（时长/套餐/闪兑） | Reply、Inline | 全体，Conversation `energy_direct_handler` @src/energy/handler_direct.py#615-655 |
| TRX Exchange | TRX 闪兑 | Reply “🔄 TRX 兑换” | 全体，Conversation `TRXExchangeHandler` @src/trx_exchange/handler.py#83-315 |
| Wallet | 个人中心 + 充值流程 | /profile、Inline | 全体，Conversation `deposit_conv` @src/wallet/profile_handler.py#43-299 |
| Address Query | 地址查询免费功能 | Reply/Inline | 全体（非 Conversation，依赖 user_data 状态）@src/address_query/handler.py#23-405 |
| Help | 帮助系统 | /help | 全体，Conversation `help_handler` @src/help/handler.py#26-193 |
| Rates | 实时 U 价 | Inline 菜单 + Reply | 全体 @src/menu/main_menu.py#180-360 |
| Clone | 免费克隆 | Inline + Reply | 全体 @src/menu/main_menu.py#144-407 |
| Support | 联系客服 | Inline + Reply | 全体 @src/menu/main_menu.py#162-407 |
| Admin Panel | 管理员面板 | /admin、Inline | owner-only，Conversation `AdminHandler` @src/bot_admin/handler.py#43-744 |
| Orders Admin | 订单查询 | /orders | owner-only，Conversation `orders_handler` @src/orders/query_handler.py#128-472 |
| Health | 系统健康 | /health | 任意用户可触发（逻辑无权限限制）@src/health.py#95-104 |

---

## 2. Section 交互明细

### 2.1 主菜单板块

- **entry**：`/start`，Reply 键盘 8 个按钮，Inline 引流按钮
- **module/file**：`src/menu/main_menu.py`
- **conversation**：否
- **role**：all

| type | 名称/文本 | handler + pattern |
| --- | --- | --- |
| command | `/start` | `MainMenuHandler.start_command` @src/menu/main_menu.py#82-122 |
| reply | `💎 Premium会员` | Premium Conversation entry @src/premium/handler.py#67-90 |
| reply | `⚡ 能量兑换` | `EnergyDirectHandler.start_energy` @src/energy/handler_direct.py#619-655 |
| reply | `🔍 地址查询` | `MainMenuHandler.handle_keyboard_button`→`AddressQueryHandler.query_address` @src/menu/main_menu.py#362-405 |
| reply | `👤 个人中心` | `ProfileHandler.profile_command` @src/menu/main_menu.py#378-382 |
| reply | `🔄 TRX 兑换` | `TRXExchangeHandler.start_exchange` @src/trx_exchange/handler.py#83-95 |
| reply | `👨‍💼 联系客服` | `MainMenuHandler.handle_keyboard_button` branch @src/menu/main_menu.py#383-391 |
| reply | `💵 实时U价` | `MainMenuHandler.show_usdt_rates_all` @src/menu/main_menu.py#392-395 |
| reply | `🎁 免费克隆` | `MainMenuHandler.handle_free_clone` @src/menu/main_menu.py#396-406 |
| inline | `menu_*` 推广按钮 | `_build_promotion_buttons` @src/menu/main_menu.py#31-80 |
| inline | `back_to_main` | `MainMenuHandler.show_main_menu` @src/menu/main_menu.py#198-205 |

子板块：Premium、能量、地址查询、个人中心、TRX 兑换、客服、实时 U 价、免费克隆。

### 2.2 Premium 会员板块

- **entry**：`/premium`、Reply `💎 Premium会员`、Inline `menu_premium`
- **module/file**：`src/premium/handler.py`
- **conversation**：`SELECTING_PACKAGE` → `ENTERING_RECIPIENTS` → `CONFIRMING_PAYMENT`
- **role**：all

| type | 名称 | handler | state/pattern |
| --- | --- | --- | --- |
| command | `/premium` | `start_premium` | entry |
| inline | `premium_3/6/12` | `package_selected` | `SELECTING_PACKAGE`, `^premium_\d+$` |
| message | 收件人文本 | `recipients_entered` | `ENTERING_RECIPIENTS` |
| inline | `confirm_payment` | `confirm_payment` | `CONFIRMING_PAYMENT` |
| inline | `cancel_order` | `cancel_order` | `CONFIRMING_PAYMENT` |
| fallback command | `/cancel` | `cancel` | 结束对话 |
| fallback inline | `menu_* / back_to_main` | `cancel_silent` | `^(menu_profile|menu_address_query|menu_energy|menu_clone|menu_support|back_to_main)$` |

子流程：套餐选择 → 收件人输入 → 支付确认。

### 2.3 能量直转板块

- **entry**：Reply `⚡ 能量兑换`、Inline `menu_energy`
- **module/file**：`src/energy/handler_direct.py`
- **conversation**：`STATE_SELECT_TYPE` / `STATE_SELECT_PACKAGE` / `STATE_INPUT_COUNT` / `STATE_INPUT_ADDRESS` / `STATE_SHOW_PAYMENT` / `STATE_INPUT_TX_HASH`
- **role**：all

| type | 文本/callback | handler | state/pattern |
| --- | --- | --- | --- |
| inline | `energy_type_*` | `select_type` | `STATE_SELECT_TYPE` |
| inline | `package_65000/131000` | `input_count` | `STATE_SELECT_PACKAGE` |
| message | 数字输入 | `input_address` | `STATE_INPUT_COUNT` |
| message | 地址输入 | `show_payment` | `STATE_INPUT_ADDRESS` |
| inline | `payment_done` | `payment_done` | `STATE_SHOW_PAYMENT` |
| message | TX Hash/跳过 | `handle_energy_tx_hash_input` | `STATE_INPUT_TX_HASH` |
| fallback inline | `energy_start` | 重新开始 |
| fallback inline | `back_to_main` | `cancel` |
| fallback inline | `menu_*` | `cancel_silent` |

子板块：时长能量、笔数套餐、闪兑。

### 2.4 TRX 兑换板块

- **entry**：Reply `🔄 TRX 兑换`
- **module/file**：`src/trx_exchange/handler.py`
- **conversation**：`INPUT_AMOUNT` → `INPUT_ADDRESS` → `CONFIRM_PAYMENT` → `INPUT_TX_HASH`
- **role**：all

| type | 文本 | handler | state/pattern |
| --- | --- | --- | --- |
| reply | `🔄 TRX 兑换` | `start_exchange` | entry |
| message | 金额 | `input_amount` | `INPUT_AMOUNT` |
| message | 收币地址 | `input_address` | `INPUT_ADDRESS` |
| inline | `trx_paid_{order}` | `confirm_payment` | `CONFIRM_PAYMENT`, `^trx_(paid|cancel)_` |
| inline | `trx_cancel_{order}` | `confirm_payment` | 取消 |
| message | TX Hash/跳过 | `handle_tx_hash_input` | `INPUT_TX_HASH` |
| fallback command | `/cancel` | `_cancel` |
| fallback inline | `menu_* / back_to_main` | `_cancel` |

### 2.5 个人中心板块

- **entry**：`/profile`、Inline `menu_profile`
- **module/file**：`src/wallet/profile_handler.py`
- **conversation**：`deposit_conv`
- **role**：all

| type | 文本/callback | handler | state/pattern |
| --- | --- | --- | --- |
| command | `/profile` | `profile_command` | - |
| inline | `menu_profile` | `profile_command_callback` | `^menu_profile$` |
| inline | `profile_balance` | `balance_query` | `^profile_balance$` |
| inline | `profile_deposit` | `start_deposit` | `^profile_deposit$`（Conversation entry） |
| message | 金额 | `receive_deposit_amount` | `AWAITING_DEPOSIT_AMOUNT` |
| inline | `profile_history` | `deposit_history` | `^profile_history$` |
| inline | `profile_back` | `back_to_profile` | `^profile_back$` |
| inline | `back_to_main` | 返回主菜单 | `^back_to_main$` |
| fallback command | `/cancel` | `ProfileHandler.cancel` | Conversation fallback |

### 2.6 地址查询板块

- **entry**：Reply `🔍 地址查询`、Inline `menu_address_query`
- **module/file**：`src/address_query/handler.py`
- **conversation**：否（依赖 `context.user_data`）
- **role**：all

| type | 文本 | handler |
| --- | --- | --- |
| inline | `menu_address_query` | `query_address` |
| inline | `cancel_query` | `cancel_query` |
| inline | `back_to_main` | 返回主菜单 |
| message | 地址文本 | `handle_address_input`（需 `awaiting_address`） |

### 2.7 帮助系统板块

- **entry**：`/help`
- **module/file**：`src/help/handler.py`
- **conversation**：`SHOWING_HELP`
- **role**：all

| type | callback_data | handler |
| --- | --- | --- |
| inline | `help_basic/payment/services/query/faq/quick` | `show_help_category` |
| inline | `help_back` | `help_back` |
| inline | `back_to_main` | `back_to_main_from_help` |
| command | `/cancel` | `cancel` |

### 2.8 实时 U 价板块

- **entry**：Reply `💵 实时U价`、Inline `menu_rates_all/bank/alipay/wechat`
- **module/file**：`src/menu/main_menu.py`
- **conversation**：否
- **role**：all

Handlers：`show_usdt_rates_all/bank/alipay/wechat`，均附 `back_to_main` 返回按钮。

### 2.9 免费克隆 / 联系客服

- `menu_clone` → `handle_free_clone`，子按钮：`menu_support`、`back_to_main`。
- Reply `🎁 免费克隆` → 文案 + Inline `menu_support`。
- Reply `👨‍💼 联系客服` 或 Inline `menu_support` → `handle_support`。

### 2.10 管理员面板

- **entry**：`/admin`、`admin_*` 等 callback
- **module/file**：`src/bot_admin/handler.py`、`bot_admin/menus.py`
- **conversation**：`EDITING_*`
- **role**：owner-only

子菜单：统计、价格、文案、系统设置、退出。各按钮 callback 详见 `AdminMenus`。

### 2.11 订单查询（管理员）

- **entry**：`/orders`
- **module/file**：`src/orders/query_handler.py`
- **conversation**：`SHOW_ORDERS`
- **role**：owner-only

Buttons：`orders_list`、`orders_filter_type`、`orders_filter_status`、`orders_filter_user`、`orders_type_*`、`orders_status_*`、`orders_page_*`、`orders_clear_filter`、`orders_back`、`orders_close`，均由 `handle_callback` 处理。

### 2.12 系统健康

- **entry**：`/health`
- **module/file**：`src/health.py`
- **conversation**：否
- **role**：所有用户可触发

---

## 3. 取消 / 返回 / 关闭按钮汇总

| 文本 | callback_data / command | Handler | 文件 |
| --- | --- | --- | --- |
| 通用返回 | `back_to_main` | `MainMenuHandler.show_main_menu` | @src/menu/main_menu.py#198-205 |
| Premium 取消 | `cancel_order` | `PremiumHandler.cancel_order` | @src/premium/handler.py#247-319 |
| Premium 静默取消 | `menu_* / back_to_main` | `PremiumHandler.cancel_silent` | 同上 |
| 地址查询取消 | `cancel_query` | `AddressQueryHandler.cancel_query` | @src/address_query/handler.py#392-404 |
| 能量取消 | `back_to_main` | `EnergyDirectHandler.cancel` | @src/energy/handler_direct.py#458-470 |
| 能量重启 | `energy_start` | `EnergyDirectHandler.start_energy` | fallback |
| TRX 取消 | `trx_cancel_{order}` | `TRXExchangeHandler.confirm_payment` | @src/trx_exchange/handler.py#262-315 |
| Admin 退出 | `admin_exit` | `AdminHandler.handle_callback` | @src/bot_admin/handler.py#75-90 |
| Orders 关闭 | `orders_close` | `handle_callback` 删除消息 | @src/orders/query_handler.py#440-448 |
| Conversation 通用 | `/cancel` | 各模块 `cancel` | 多处 |

命名分散：`cancel_order`、`cancel_query`、`back_to_main`、`orders_close`、`trx_cancel_*` 等。

---

## 4. 高风险交互点

1. **订单查询 CallbackQueryHandler 未设 pattern**：@src/orders/query_handler.py#465-467 直接捕获所有 callback，若 group 冲突可能截获其他模块。
2. **地址查询 MessageHandler 捕获所有文本**：@src/bot.py#151-157（group=1）仍可能与其它自由输入冲突；`context.user_data.clear()` 会清理其他模块状态。
3. **取消/返回 callback 命名不统一**：`cancel_order/cancel_query/back_to_main/trx_cancel_*` 等难以统一处理。
4. **通配 fallback pattern 需维护**：Premium、TRX、能量等对话仅覆盖部分 `menu_*`，新增按钮需同步更新 pattern。
5. **地址查询无 Conversation**：依靠 `context.user_data['awaiting_address']`，与其他对话共享同一容器，易覆写。
6. **管理员面板 callback 前缀广**：`^(admin_|price_|premium_edit_|energy_edit_|content_|settings_|edit_trx_rate|confirm_)` 若其他模块复用前缀可能冲突。
7. **TRX 兑换 fallback 不完整**：仅覆盖 `menu_*` + `back_to_main`，若点击其他 inline（如 admin 菜单）可能无法退出。

---

## 5. 建议的下一步

1. **统一取消/返回回调命名**：抽象通用 `cancel`/`back` handler，所有模块复用同一 callback 前缀，避免多处维护。
2. **订单查询回调细分**：在 `ConversationHandler` 中增加精确 pattern 或拆分 Handler，防止抢占其他 callback。
3. **将地址查询纳入 Conversation**：通过 entry/states 管理状态，杜绝 `context.user_data.clear()` 对其他模块的影响。
4. **全面审查 `menu_*` fallback 列表**：确保各对话的静默取消 pattern 覆盖所有主菜单按钮，避免新增按钮导致对话未被正确终止。

---

> 本文档由源码扫描整理，可作为后续交互重构的参考，集中展示命令、按钮、Conversation 与高风险点。
