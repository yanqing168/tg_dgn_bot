# 🚀 快速测试 - 管理员面板

## 📱 立即开始测试

### Bot 信息
```
Bot 用户名: @Dhdjdbrj_bot
Bot 状态: ✅ 运行中
PID: 294871
```

### 第一步：获取你的 Telegram 用户 ID

1. 在 Telegram 搜索 `@userinfobot`
2. 发送任意消息
3. 记下返回的用户 ID

### 第二步：配置 Owner ID

```bash
# 编辑 .env 文件
cd /workspaces/tg_dgn_bot
nano .env

# 修改这一行（将 123456789 替换为你的真实 ID）
BOT_OWNER_ID=你的真实ID

# 保存并退出（Ctrl+X, Y, Enter）
```

### 第三步：重启 Bot

```bash
# 停止旧进程
pkill -f "python3 -m src.bot"

# 等待 2 秒
sleep 2

# 启动新进程
nohup python3 -m src.bot > logs/bot.log 2>&1 &

# 查看日志确认启动成功
tail -20 logs/bot.log
```

### 第四步：开始测试

1. 在 Telegram 中搜索 `@Dhdjdbrj_bot`
2. 点击 "Start"
3. 发送命令：`/admin`
4. 你应该看到管理面板主菜单（6个按钮）

---

## ⚡ 核心测试流程（5分钟）

### 1️⃣ 测试访问权限
```
发送: /admin
预期: 显示管理面板主菜单
```

### 2️⃣ 测试统计查询
```
点击: 📊 统计数据
预期: 显示订单/用户/收入统计
```

### 3️⃣ 测试价格查看
```
点击: 💰 价格配置 → 💎 Premium 会员
预期: 显示 3/6/12个月价格（$10/$18/$30）
```

### 4️⃣ 测试价格修改
```
点击: ✏️ 3个月
输入: 12
预期: 显示"价格已更新"，新价格 $12.0
```

### 5️⃣ 测试系统状态
```
点击: ⚙️ 系统设置 → 📊 系统状态
预期: Redis、数据库、Bot 都显示 ✅ 正常
```

---

## 🎯 测试成功标志

✅ 所有按钮正常响应  
✅ 价格修改立即生效  
✅ 数据库正确保存配置  
✅ 审计日志记录操作  
✅ 非 Owner 用户无法访问  

---

## 📊 实时监控

### 查看 Bot 日志（实时）
```bash
tail -f logs/bot.log
```

### 查看数据库（价格配置）
```bash
sqlite3 data/bot.db "SELECT * FROM price_configs;"
```

### 查看审计日志（最近10条）
```bash
sqlite3 data/bot.db "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10;"
```

---

## 🆘 遇到问题？

### Bot 没反应？
```bash
# 检查进程
ps aux | grep "python3 -m src.bot"

# 查看日志
tail -50 logs/bot.log
```

### 显示"权限不足"？
```bash
# 检查配置
grep "BOT_OWNER_ID" .env

# 你的配置应该是你的真实 Telegram 用户 ID
```

### 按钮点击无效？
```bash
# 查看实时日志
tail -f logs/bot.log

# 应该能看到你的操作记录
```

---

## ✅ 测试完成后

1. ✅ 在测试指南中勾选所有完成的测试项
2. 📸 保存测试截图
3. 📝 记录发现的问题
4. 🎉 庆祝功能正常运行！

---

**现在就开始测试吧！** 🚀
