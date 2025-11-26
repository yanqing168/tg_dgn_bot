# TG DGN Bot - Telegram 多功能数字服务平台 🚀

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Bot Status](https://img.shields.io/badge/status-active-success.svg)]()
[![API](https://img.shields.io/badge/API-REST-green.svg)](http://localhost:8001/api/docs)
[![Architecture](https://img.shields.io/badge/Architecture-V2-blue.svg)](docs/NEW_ARCHITECTURE.md)

## 📖 项目简介

一个功能完善的 Telegram Bot 数字服务平台，提供多种数字资产交易、会员服务、能量兑换等功能。支持 USDT-TRC20 支付，具备完整的管理后台和自动化交付系统。

### ✨ 核心特性

- 🔐 **USDT-TRC20 支付系统** - 固定地址 + 0.001-0.999 唯一后缀识别
- 💎 **Premium 会员直充** - 支持 3/6/12 个月套餐，自动交付
- ⚡ **能量兑换服务** - 时长能量、笔数套餐、USDT/TRX 闪兑
- 🔄 **TRX 闪兑服务** - 实时汇率，快速兑换
- 👤 **个人中心系统** - 余额管理、充值提现、交易记录
- 🔍 **地址查询功能** - 波场地址验证，智能限频（可配置）
- 💵 **实时 USDT 汇率** - 多渠道报价（银行卡/支付宝/微信）
- 🎁 **免费克隆服务** - 一键克隆 Bot 功能
- 👨‍💼 **管理员面板** - 价格配置、内容管理、订单查询
- 📊 **审计日志系统** - 完整的操作记录和追踪

## 🎯 功能模块详情

### 1. 支付系统
- **USDT-TRC20**: 波场网络 USDT 收款，自动确认
- **唯一后缀机制**: 0.001-0.999 后缀池，自动分配和回收
- **订单管理**: 自动超时处理，状态追踪

### 2. Premium 会员
- **套餐选择**: 3个月、6个月、12个月
- **批量收件**: 支持多个收件人，格式灵活
- **自动交付**: 支付确认后自动发放会员

### 3. 能量服务
- **时长能量**: 65000/131000 能量，1-20笔
- **笔数套餐**: 灵活的套餐配置
- **闪兑服务**: USDT/TRX 直接兑换能量

### 4. TRX 兑换
- **实时汇率**: 动态价格更新
- **快速交易**: 支付确认后自动转账
- **交易追踪**: 完整的交易哈希记录

### 5. 管理后台
- **价格管理**: Premium、能量、TRX 汇率配置
- **内容管理**: 欢迎消息、帮助文档等
- **订单查询**: 多维度筛选和导出
- **系统设置**: 超时时间、限频规则等

## 📁 项目结构

```
tg_dgn_bot/
├── 📂 src/                        # 源代码目录
│   ├── 🤖 bot.py                  # Bot 主程序入口
│   ├── ⚙️ config.py               # 配置管理
│   ├── 💾 database.py             # 数据库模型
│   ├── 📂 menu/                   # 菜单系统
│   │   ├── main_menu.py          # 主菜单和 /start
│   │   └── simple_handlers.py    # 简单功能处理器
│   ├── 📂 payments/              # 支付系统
│   │   ├── suffix_manager.py     # 后缀管理器
│   │   ├── amount_calculator.py  # 金额计算
│   │   └── order.py              # 订单管理
│   ├── 📂 premium/               # Premium 会员
│   │   ├── handler.py           # 会话处理器
│   │   ├── recipient_parser.py  # 收件人解析
│   │   └── delivery.py          # 自动交付
│   ├── 📂 wallet/                # 钱包系统
│   │   ├── wallet_manager.py    # 余额管理
│   │   └── profile_handler.py   # 个人中心
│   ├── 📂 energy/                # 能量服务
│   │   ├── handler.py           # 能量兑换
│   │   └── handler_direct.py    # 直转模式
│   ├── 📂 trx_exchange/          # TRX 兑换
│   │   └── handler.py           # 兑换处理
│   ├── 📂 address_query/         # 地址查询
│   │   ├── handler.py           # 查询处理
│   │   └── validator.py         # 地址验证
│   ├── 📂 rates/                 # 汇率服务
│   │   └── service.py           # OKX 汇率获取
│   ├── 📂 bot_admin/             # 管理后台
│   │   ├── handler.py           # 管理面板
│   │   ├── config_manager.py    # 配置管理
│   │   └── audit_log.py         # 审计日志
│   ├── 📂 orders/                # 订单管理
│   │   └── query_handler.py     # 订单查询
│   ├── 📂 help/                  # 帮助系统
│   │   └── handler.py           # 帮助文档
│   └── 📂 common/                # 公共组件
│       ├── decorators.py        # 装饰器
│       └── content_helper.py    # 内容管理
│
├── 📂 tests/                     # 测试套件
│   ├── test_*.py                # 单元测试
│   └── conftest.py             # 测试配置
│
├── 📂 scripts/                   # 实用脚本
│   ├── start_bot.sh            # 启动脚本
│   ├── stop_bot.sh             # 停止脚本
│   ├── backup_dbs.py           # 数据库备份
│   └── validate_config.py      # 配置验证
│
├── 📂 docs/                      # 文档目录
│   ├── QUICK_START.md          # 快速开始
│   ├── DEPLOYMENT.md           # 部署指南
│   ├── ADMIN_PANEL_GUIDE.md    # 管理指南
│   └── ARCHITECTURE.md         # 架构说明
│
├── 📄 requirements.txt          # Python 依赖
├── 📄 .env.example             # 环境变量示例
├── 📄 docker-compose.yml       # Docker 编排
├── 📄 Dockerfile               # Docker 镜像
└── 💾 tg_bot.db               # SQLite 数据库
```

## 🆕 V2 新架构特性

### 标准化模块系统
- **BaseModule**: 所有模块的基类，统一接口
- **MessageFormatter**: HTML消息格式化，自动转义特殊字符  
- **ModuleStateManager**: 模块状态管理，隔离各模块数据
- **ModuleRegistry**: 模块注册中心，动态管理模块

### REST API 接口
完整的REST API支持，可通过HTTP接口管理Bot：

```bash
# 健康检查
GET /api/health

# 模块管理
GET /api/modules
PATCH /api/modules/{name}/status

# Premium功能
POST /api/premium/check-eligibility
GET /api/premium/packages

# 订单管理
POST /api/orders
GET /api/orders/{order_id}
```

📚 详细API文档：http://localhost:8001/api/docs

### 启动新版本

```bash
# 启动 Bot V2（包含API服务）
python -m src.bot_v2

# 或仅启动API服务（用于测试）
python test_bot_v2.py
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.11 或更高版本
- pip 包管理器
- SQLite3（内置）

### 2. 安装步骤

```bash
# 克隆项目
git clone https://github.com/your-username/tg_dgn_bot.git
cd tg_dgn_bot

# 安装依赖
pip install -r requirements.txt

# 复制环境变量配置
cp .env.example .env

# 编辑 .env 文件，设置必要的配置
# BOT_TOKEN=your_bot_token_here
# BOT_OWNER_ID=your_telegram_user_id
# USDT_TRC20_RECEIVE_ADDR=your_trc20_address
```

### 3. 启动 Bot

```bash
# 启动 V2 版本（推荐）
python -m src.bot_v2

# 或启动旧版本
python -m src.bot

# 或使用脚本
bash scripts/start_bot.sh
```

### 4. 初始化配置

```bash
# 初始化管理员配置
python scripts/init_admin_config.py

# 初始化内容配置
python scripts/init_content_configs.py
```

## 🎮 使用指南

### 用户命令

- `/start` - 显示主菜单
- `/help` - 查看帮助文档
- `/profile` - 个人中心
- `/premium` - Premium 会员购买
- `/health` - 系统健康检查

### 管理员命令

- `/admin` - 管理面板（仅限 owner）
- `/orders` - 订单查询（仅限 owner）

### 按钮功能

#### Inline 按钮（主菜单）
- 💎 开通会员 - Premium 会员购买
- 👤 个人中心 - 查看余额和交易记录
- ⚡ 能量兑换 - 能量服务
- 🔍 地址查询 - 查询波场地址
- 🎁 免费克隆 - 克隆 Bot 功能
- 👨‍💼 联系客服 - 客服支持

#### Reply 键盘（底部菜单）
- 💎 Premium会员 - 会员服务
- ⚡ 能量兑换 - 能量交易
- 🔍 地址查询 - 地址验证
- 👤 个人中心 - 账户管理
- 🔄 TRX 兑换 - TRX 交易
- 👨‍💼 联系客服 - 客服支持
- 💵 实时U价 - USDT 汇率
- 🎁 免费克隆 - 克隆服务

## 🔧 配置说明

### 环境变量

```env
# Bot 配置
BOT_TOKEN=your_telegram_bot_token
BOT_OWNER_ID=your_telegram_user_id

# 支付配置
USDT_TRC20_RECEIVE_ADDR=your_trc20_wallet_address

# 数据库配置
DATABASE_URL=sqlite:///./tg_bot.db

# Redis 配置（可选）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Webhook 配置（可选）
USE_WEBHOOK=false
WEBHOOK_URL=https://your-domain.com
```

### 价格配置

通过管理面板动态配置：
- Premium 会员价格（3/6/12 个月）
- 能量价格（时长/套餐）
- TRX 兑换汇率

## 📊 数据库架构

### 主要数据表

- `users` - 用户信息和余额
- `orders` - 通用订单表
- `deposit_orders` - 充值订单
- `energy_orders` - 能量订单
- `trx_exchange_orders` - TRX 兑换订单
- `suffix_allocations` - 后缀分配记录
- `address_query_logs` - 地址查询限频
- `audit_logs` - 审计日志
- `price_configs` - 价格配置
- `content_configs` - 内容配置
- `setting_configs` - 系统设置

## 🐳 Docker 部署

```bash
# 构建镜像
docker build -t tg-dgn-bot .

# 使用 docker-compose 启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/test_premium_order.py

# 生成覆盖率报告
pytest --cov=src tests/
```

## 📈 监控与日志

- 日志文件：自动输出到控制台
- 错误追踪：通过装饰器自动捕获
- 审计日志：记录所有管理操作
- 健康检查：`/health` 命令

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [APScheduler](https://github.com/agronholm/apscheduler)

## 📞 联系方式

- GitHub Issues: [提交问题](https://github.com/your-username/tg_dgn_bot/issues)
- Telegram: @your_support_bot

---

**最后更新**: 2025-11-26  
**版本**: 2.0.0  
**状态**: 生产就绪 ✅  
**测试**: 430 passed, 0 failed
