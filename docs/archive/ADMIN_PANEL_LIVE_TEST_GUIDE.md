# 管理员面板实时测试指南

## 🤖 Bot 信息
- **Bot 用户名**: @Dhdjdbrj_bot
- **Bot Token**: 8229132294:AAGIgDjK-q5AdTQyQQ9RplbJYkW3zvaFVdQ
- **测试环境**: 开发环境（Polling 模式）
- **启动时间**: 2025-10-29 14:54:24 UTC
- **PID**: 294829

## 🔐 重要：配置你的 Telegram 用户 ID

### 步骤 1: 获取你的 Telegram 用户 ID

1. 在 Telegram 中找到 `@userinfobot`
2. 给它发送任意消息
3. 它会返回你的用户 ID（例如：`User ID: 123456789`）
4. 记下这个数字

### 步骤 2: 更新配置文件

编辑 `.env` 文件，将 `BOT_OWNER_ID` 替换为你的真实用户 ID：

```bash
# 当前配置（示例值）
BOT_OWNER_ID=123456789

# 修改为你的真实 ID
BOT_OWNER_ID=你的用户ID
```

### 步骤 3: 重启 Bot

```bash
cd /workspaces/tg_dgn_bot
pkill -f "python3 -m src.bot"
sleep 2
nohup python3 -m src.bot > logs/bot.log 2>&1 &
```

---

## 📋 测试清单

### ✅ 测试 1: 访问管理面板

1. 在 Telegram 中搜索 `@Dhdjdbrj_bot`
2. 点击 "Start" 或发送 `/start`
3. 发送命令：`/admin`

**预期结果**：
- 如果你是 Owner：显示管理面板主菜单（6个按钮）
- 如果不是 Owner：显示"权限不足"提示

**测试截图位置**：
- 保存到 `docs/screenshots/admin_panel_01_main_menu.png`

---

### ✅ 测试 2: 查看统计数据

1. 在管理面板中点击 `📊 统计数据`
2. 查看订单、用户、收入统计

**预期结果**：
- 显示完整统计报告
- 包含订单数量、用户数量、收入金额
- 数据格式正确（带货币符号、数字格式化）

**测试截图位置**：
- 保存到 `docs/screenshots/admin_panel_02_statistics.png`

---

### ✅ 测试 3: 查看价格配置

1. 点击 `🔙 返回` 回到主菜单
2. 点击 `💰 价格配置`
3. 点击 `💎 Premium 会员`

**预期结果**：
- 显示当前 Premium 价格
  - 3个月：$10.0 USDT
  - 6个月：$18.0 USDT
  - 12个月：$30.0 USDT
- 显示编辑按钮

**测试截图位置**：
- 保存到 `docs/screenshots/admin_panel_03_premium_prices.png`

---

### ✅ 测试 4: 修改 Premium 价格

1. 点击 `✏️ 3个月` 编辑按钮
2. 输入新价格：`12`
3. 确认修改

**预期结果**：
- 显示"价格已更新"成功提示
- 新价格：$12.0 USDT
- 生效时间：立即
- 可以再次查看确认价格已改变

**测试内容**：
- 价格修改是否成功
- 数据库是否更新
- 审计日志是否记录

**测试截图位置**：
- 保存到 `docs/screenshots/admin_panel_04_price_update_success.png`

---

### ✅ 测试 5: 查看 TRX 汇率

1. 返回价格配置菜单
2. 点击 `🔄 TRX 汇率`
3. 查看当前汇率

**预期结果**：
- 显示当前汇率：1 USDT = 3.05 TRX
- 显示示例计算
- 显示修改按钮

**测试截图位置**：
- 保存到 `docs/screenshots/admin_panel_05_trx_rate.png`

---

### ✅ 测试 6: 修改 TRX 汇率

1. 点击 `✏️ 修改汇率`
2. 输入新汇率：`3.15`
3. 确认修改

**预期结果**：
- 显示"汇率已更新"成功提示
- 新汇率：1 USDT = 3.15 TRX
- 显示新示例计算
- 生效时间：立即

**测试截图位置**：
- 保存到 `docs/screenshots/admin_panel_06_rate_update_success.png`

---

### ✅ 测试 7: 查看能量价格

1. 返回价格配置菜单
2. 点击 `⚡ 能量价格`
3. 查看所有能量价格

**预期结果**：
- 小能量 (6.5万)：3.0 TRX
- 大能量 (13.1万)：6.0 TRX
- 笔数套餐单价：3.6 TRX/笔
- 显示编辑按钮

**测试截图位置**：
- 保存到 `docs/screenshots/admin_panel_07_energy_prices.png`

---

### ✅ 测试 8: 系统设置

1. 返回主菜单
2. 点击 `⚙️ 系统设置`
3. 浏览所有设置选项

**预期结果**：
- 显示 4 个设置选项：
  - ⏰ 订单超时
  - 🔍 查询限频
  - 🗑️ 清理缓存
  - 📊 系统状态

**测试截图位置**：
- 保存到 `docs/screenshots/admin_panel_08_settings_menu.png`

---

### ✅ 测试 9: 查看系统状态

1. 在系统设置菜单点击 `📊 系统状态`
2. 查看各组件状态

**预期结果**：
- Redis：✅ 正常
- 数据库：✅ 正常
- Bot：✅ 运行中

**测试截图位置**：
- 保存到 `docs/screenshots/admin_panel_09_system_status.png`

---

### ✅ 测试 10: 权限验证

1. 使用另一个 Telegram 账号（非 Owner）
2. 向 Bot 发送 `/admin` 命令

**预期结果**：
- 显示 "⛔ 权限不足" 提示
- 提示此功能仅限管理员使用
- 无法访问管理面板

**测试截图位置**：
- 保存到 `docs/screenshots/admin_panel_10_access_denied.png`

---

## 🔍 数据验证

### 验证价格修改是否持久化

```bash
# 查询数据库中的价格配置
cd /workspaces/tg_dgn_bot
sqlite3 data/bot.db "SELECT * FROM price_configs;"
```

**预期输出**：
```
1|premium_3_months|12.0|Premium 3个月价格|你的用户ID|2025-10-29 14:XX:XX
2|premium_6_months|18.0|Premium 6个月价格|0|2025-10-29 14:31:38
...
```

### 验证审计日志

```bash
# 查询最近的审计日志
sqlite3 data/bot.db "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10;"
```

**预期输出**：
```
日志ID|你的用户ID|update_price|premium_3_months|修改为 $12.0|success||2025-10-29 14:XX:XX
```

---

## 📊 测试结果记录表

| 测试项 | 状态 | 备注 |
|-------|------|------|
| 1. 访问管理面板 | ⬜ 待测试 | |
| 2. 查看统计数据 | ⬜ 待测试 | |
| 3. 查看价格配置 | ⬜ 待测试 | |
| 4. 修改 Premium 价格 | ⬜ 待测试 | |
| 5. 查看 TRX 汇率 | ⬜ 待测试 | |
| 6. 修改 TRX 汇率 | ⬜ 待测试 | |
| 7. 查看能量价格 | ⬜ 待测试 | |
| 8. 系统设置菜单 | ⬜ 待测试 | |
| 9. 查看系统状态 | ⬜ 待测试 | |
| 10. 权限验证 | ⬜ 待测试 | |

**测试通过标准**：10/10 ✅

---

## 🐛 常见问题

### Q1: 发送 `/admin` 后没有反应？

**排查步骤**：
1. 检查 Bot 是否在运行：`ps aux | grep "python3 -m src.bot"`
2. 查看 Bot 日志：`tail -50 logs/bot.log`
3. 确认 BOT_OWNER_ID 是否配置正确

### Q2: 显示"权限不足"？

**原因**：你的 Telegram 用户 ID 与 `.env` 中的 `BOT_OWNER_ID` 不匹配。

**解决方案**：
1. 获取你的真实用户 ID（通过 @userinfobot）
2. 更新 `.env` 文件
3. 重启 Bot

### Q3: 价格修改后没有生效？

**排查步骤**：
1. 检查数据库：`sqlite3 data/bot.db "SELECT * FROM price_configs;"`
2. 查看审计日志：是否有修改记录
3. 尝试重新修改并观察日志输出

### Q4: Bot 启动失败？

**排查步骤**：
1. 查看完整日志：`cat logs/bot.log`
2. 检查依赖是否完整：`pip install -r requirements.txt`
3. 检查 Redis 是否运行：`redis-cli ping`

---

## 📝 测试后续步骤

完成所有测试后：

1. **收集测试结果**
   - 记录所有测试项的通过/失败状态
   - 保存所有截图到 `docs/screenshots/`
   
2. **生成测试报告**
   - 更新 `docs/ADMIN_PANEL_TEST_REPORT.md`
   - 添加实际测试结果和截图

3. **发现的 Bug**
   - 记录到 GitHub Issues
   - 标注优先级和修复计划

4. **下一步集成**
   - 集成动态价格到 Premium 处理器
   - 集成动态价格到 Energy 处理器
   - 实现文案配置功能

---

**测试负责人**: 你  
**测试时间**: 现在开始  
**预计耗时**: 15-20 分钟  
**测试环境**: 开发环境  
**Bot 状态**: ✅ 运行中
