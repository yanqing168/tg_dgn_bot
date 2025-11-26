# 🚀 快速上手指南

本指南将帮助你在 5 分钟内完成 Bot 的部署和配置。

---

## 📋 前置要求

- ✅ Python 3.11+
- ✅ Redis 7.0+
- ✅ Telegram Bot Token（通过 [@BotFather](https://t.me/BotFather) 创建）
- ✅ 波场钱包地址（用于接收 USDT/TRX）
- ✅ trxno.com 代理账号（用于能量服务）

---

## 🔧 5分钟快速部署

### 步骤 1: 克隆项目

```bash
git clone https://github.com/Jack123-UU/tg_dgn_bot.git
cd tg_dgn_bot
```

### 步骤 2: 安装依赖

```bash
pip install -r requirements.txt
```

### 步骤 3: 配置环境变量

复制配置模板并编辑：

```bash
cp .env.example .env
vim .env  # 或使用你喜欢的编辑器
```

**最小配置（仅需 3 个必填项）**：

```bash
# Telegram Bot
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# USDT TRC20 收款地址（用于 Premium + 余额充值）
USDT_TRC20_RECEIVE_ADDR=TYourUSDTReceiveAddress

# HMAC 签名密钥（随机生成）
WEBHOOK_SECRET=your_webhook_secret_key_random_string
```

**可选配置（启用能量服务）**：

```bash
# 能量代理地址（TRX 直转模式）
ENERGY_RENT_ADDRESS=TYourEnergyRentAddress      # 时长能量收TRX地址
ENERGY_PACKAGE_ADDRESS=TYourPackageAddress      # 笔数套餐收USDT地址
ENERGY_FLASH_ADDRESS=TYourFlashExchangeAddr     # 闪兑收USDT地址
```

### 步骤 4: 启动 Redis

```bash
# 如果未安装 Redis，请先安装
# Ubuntu/Debian:
sudo apt-get install redis-server

# macOS:
brew install redis

# 启动 Redis
redis-server
```

### 步骤 5: 运行测试（可选）

```bash
python -m pytest tests/ -m "not redis" -v
```

### 步骤 6: 启动 Bot

```bash
./scripts/start_bot.sh
```

或直接运行：

```bash
python -m src.bot
```

---

## ✅ 验证部署

### 1. 检查 Bot 是否在线

在 Telegram 中找到你的 Bot，发送 `/start`，应该看到欢迎消息。

### 2. 测试各个功能

| 功能 | 测试方法 | 预期结果 |
|------|---------|---------|
| 主菜单 | 发送 `/start` | 显示欢迎语和按钮 |
| 地址查询 | 点击"地址监听" | 提示输入地址 |
| 个人中心 | 点击"个人中心" | 显示余额信息 |
| Premium | 点击"飞机会员" | 显示套餐选择 |
| 能量服务 | 点击"能量闪租" | 显示能量类型选择 |

---

## 🎯 核心功能配置

### 功能 1: Premium 会员直充 ✅ 开箱即用

**需要配置**：
- `BOT_TOKEN`
- `USDT_TRC20_RECEIVE_ADDR`
- `WEBHOOK_SECRET`

**用户流程**：
1. 点击"飞机会员"
2. 选择套餐（3/6/12 个月）
3. 输入收件人（@username）
4. 转账 USDT（精确到 3 位小数）
5. 自动交付到收件人账户

**测试建议**：
- 先用小金额测试（3个月套餐，约 $10）
- 确认 TRC20 回调正常工作

---

### 功能 2: 余额管理 ✅ 开箱即用

**需要配置**：
- `BOT_TOKEN`
- `USDT_TRC20_RECEIVE_ADDR`
- `WEBHOOK_SECRET`

**用户流程**：
1. 点击"个人中心"
2. 选择"充值 USDT"
3. 输入充值金额
4. 转账 USDT（精确到 3 位小数）
5. 2-5 分钟自动到账

**测试建议**：
- 先充值小金额（如 1 USDT）
- 查看余额记录是否正确

---

### 功能 3: 地址查询 ✅ 开箱即用（免费）

**需要配置**：
- `BOT_TOKEN`
- `ADDRESS_QUERY_RATE_LIMIT_MINUTES`（默认 30，管理后台可调）

**用户流程**：
1. 点击"地址监听"
2. 输入波场地址（T 开头）
3. 查看地址信息
4. 点击按钮访问区块链浏览器

**特点**：
- 完全免费
- 管理员可配置的限频（默认 30 分钟/人）
- 无需配置 TRON API

---

### 功能 4: 能量服务 ⚠️ 需要额外配置

**需要配置**：
1. **trxno.com 代理账号**
   - 注册：https://trxno.com
   - 登录后台

2. **设置代理地址**
   - 能量租用地址：收 TRX 的地址
   - 笔数套餐地址：收 USDT 的地址
   - 闪兑地址：收 USDT 的地址

3. **配置 .env**
   ```bash
   ENERGY_RENT_ADDRESS=TYourEnergyRentAddress
   ENERGY_PACKAGE_ADDRESS=TYourPackageAddress
   ENERGY_FLASH_ADDRESS=TYourFlashExchangeAddr
   ```

4. **设置价格和限制**
   - 6.5万能量 = 3 TRX
   - 13.1万能量 = 6 TRX
   - 笔数限制：1-20笔

**用户流程**：
1. 点击"能量闪租"
2. 选择能量类型（时长能量/笔数套餐/闪兑）
3. 选择套餐和数量
4. 输入接收地址
5. 转账到代理地址（TRX 或 USDT）
6. 6秒自动到账

**测试建议**：
- 先用能量闪租测试（最小 3 TRX）
- 确认代理后台地址配置正确
- 测试真实转账流程

---

## 🔐 安全配置建议

### 1. 生成强密钥

```bash
# 生成 WEBHOOK_SECRET
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. 保护 .env 文件

```bash
# 设置文件权限（仅所有者可读写）
chmod 600 .env
```

### 3. 定期备份数据库

```bash
# 备份 SQLite 数据库
cp tg_dgn_bot.db tg_dgn_bot.db.backup
```

---

## 🐛 常见问题

### Q1: Bot 启动失败

**可能原因**：
- BOT_TOKEN 配置错误
- Redis 未启动
- 端口被占用

**解决方法**：
```bash
# 检查配置
python scripts/validate_config.py

# 检查 Redis
redis-cli ping  # 应返回 PONG

# 查看日志
tail -f bot.log
```

### Q2: 支付未到账

**可能原因**：
- 转账金额不匹配（后缀错误）
- TRC20 回调未配置
- 订单已过期（超过当前配置的有效期）

**解决方法**：
```bash
# 查看订单日志
grep "order_id" bot.log

# 检查 Redis 订单状态
redis-cli HGETALL "order:ORDER_ID"
```

### Q3: 能量未到账

**可能原因**：
- 代理地址配置错误
- 转账金额错误（非整数）
- 代理后台余额不足

**解决方法**：
1. 检查 .env 中的代理地址配置
2. 登录 trxno.com 后台查看余额
3. 确认用户转账金额正确

### Q4: 地址查询失败

**可能原因**：
- 限频中（未到当前配置的冷却时间）
- 地址格式错误

**解决方法**：
- 等待限频时间结束
- 确认地址格式（T 开头，34 位）

---

## 📊 监控和维护

### 日常检查

```bash
# 检查 Bot 状态
ps aux | grep "python -m src.bot"

# 查看实时日志
tail -f bot.log

# 检查 Redis 连接
redis-cli INFO stats

# 查看订单统计
redis-cli KEYS "order:*" | wc -l
```

### 定期维护

| 任务 | 频率 | 命令 |
|------|------|------|
| 备份数据库 | 每天 | `cp tg_dgn_bot.db backup/` |
| 清理过期订单 | 每周 | Redis TTL 自动过期 |
| 查看错误日志 | 每天 | `grep ERROR bot.log` |
| 检查代理余额 | 每天 | 登录 trxno.com 后台 |

---

## 🚀 进阶配置

### 1. 配置 TRC20 回调（推荐）

如果你有公网 IP 或服务器，可以配置 TRC20 回调实现自动到账：

```python
# webhook/server.py
from flask import Flask, request
from src.payments.trc20_handler import TRC20CallbackHandler

app = Flask(__name__)
handler = TRC20CallbackHandler()

@app.route('/webhook/trc20', methods=['POST'])
async def trc20_callback():
    data = request.json
    await handler.handle_callback(data)
    return {'status': 'ok'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

### 2. 配置 TRON API（可选）

如果需要更详细的地址查询信息：

```bash
# .env
TRON_API_URL=https://api.trongrid.io
TRON_API_KEY=your_trongrid_api_key
```

### 3. 自定义欢迎语

```bash
# .env
WELCOME_MESSAGE="👋 欢迎 {first_name}！\n\n您的自定义欢迎语..."
```

### 4. 添加引流按钮

```bash
# .env
PROMOTION_BUTTONS='[{"text": "💎 开会员", "callback": "menu_premium"}],[{"text": "📱 频道", "url": "https://t.me/yourchannel"}]'
```

---

## 📚 下一步

- 📖 阅读 [docs/PAYMENT_MODES.md](PAYMENT_MODES.md) 了解支付方式详解
- 🧪 运行完整测试套件：`pytest tests/ -v`
- 📊 查看 [docs/IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) 了解实现细节
- 💬 加入社区讨论：[GitHub Issues](https://github.com/Jack123-UU/tg_dgn_bot/issues)

---

## 🆘 获取帮助

遇到问题？

1. 查看 [常见问题](#-常见问题)
2. 搜索 [GitHub Issues](https://github.com/Jack123-UU/tg_dgn_bot/issues)
3. 提交新的 Issue
4. 联系开发者：[@Jack123-UU](https://github.com/Jack123-UU)

---

**祝你使用愉快！🎉**
