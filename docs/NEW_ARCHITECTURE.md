# 🏗️ 新架构文档

## 概述

Bot V2 采用了全新的标准化模块架构，提供了更好的可维护性、稳定性和扩展性。

## 📊 系统架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                    TG DGN Bot V2 系统架构                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  👤 用户层                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Telegram 用户  →  Bot 界面  →  命令/按钮交互          │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  🤖 应用层                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Bot V2 主程序 (src/bot_v2.py)                        │   │
│  │  ├─ ModuleRegistry (模块注册中心)                     │   │
│  │  ├─ SafeConversationHandler (统一对话处理)            │   │
│  │  ├─ NavigationManager (统一导航管理)                  │   │
│  │  └─ REST API Layer (FastAPI)                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  📦 标准化模块层                                              │
│  ┌───────────┬───────────┬───────────┬──────────────┐      │
│  │ Premium   │  Energy   │   TRX     │   Wallet     │      │
│  │ ✅ 已完成  │ ✅ 已完成  │  📋 计划中 │  📋 计划中    │      │
│  ├───────────┼───────────┼───────────┼──────────────┤      │
│  │ Address   │   Menu    │   Help    │   Admin      │      │
│  │ ✅ 已完成  │ ✅ 已完成  │  📋 计划中 │  📋 计划中    │      │
│  └───────────┴───────────┴───────────┴──────────────┘      │
│                           ↓                                  │
│  💾 数据层                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  SQLite 数据库 (tg_bot.db)                            │   │
│  │  ├─ 用户数据  ├─ 订单记录  ├─ 配置信息  └─ 审计日志    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## 核心特性

### 1. 标准化模块系统

- **BaseModule**: 所有模块的基类
- **MessageFormatter**: 统一的消息格式化（HTML）
- **ModuleStateManager**: 模块状态管理
- **ModuleRegistry**: 模块注册中心

### 2. REST API接口

提供完整的REST API访问Bot功能：

#### 系统接口
- `GET /api/health` - 健康检查
- `GET /api/stats` - 系统统计（需认证）

#### 模块管理
- `GET /api/modules` - 列出所有模块
- `GET /api/modules/{name}` - 获取模块详情
- `PATCH /api/modules/{name}/status` - 启用/禁用模块（需认证）

#### Premium功能
- `POST /api/premium/check-eligibility` - 检查开通资格（需认证）
- `GET /api/premium/packages` - 获取套餐列表

#### 订单管理
- `POST /api/orders` - 创建订单（需认证）
- `GET /api/orders/{id}` - 获取订单详情（需认证）
- `GET /api/orders/user/{user_id}` - 用户订单列表（需认证）

#### 钱包功能
- `GET /api/wallet/balance/{user_id}` - 获取余额（需认证）
- `POST /api/wallet/deposit` - 增加余额（需认证）

#### 消息功能
- `POST /api/message/send` - 发送消息（需认证）
- `POST /api/message/broadcast` - 广播消息（需认证）

#### 其他功能
- `GET /api/rates/usdt` - USDT实时汇率
- `GET /api/energy/packages` - 能量套餐
- `POST /api/energy/calculate` - 计算能量价格

### 3. 认证机制

使用API密钥认证：
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8001/api/stats
```

### 4. 已解决的问题

✅ **Premium Markdown解析错误** - 统一使用HTML格式
✅ **主菜单重复提示问题** - 优化键盘显示逻辑
✅ **模块管理混乱** - 统一注册中心
✅ **缺少API接口** - 完整REST API

## 启动方式

### 开发环境

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 启动新版本（包含API）
python -m src.bot_v2

# 或者只启动Bot（旧版本）
python -m src.bot
```

### 生产环境

```bash
# 使用Docker
docker-compose up -d

# 或使用PM2
pm2 start src/bot_v2.py --interpreter python3
```

## 架构图

```
┌─────────────────────────────────────┐
│         Telegram Users              │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│      Telegram Bot API               │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│         Bot Application             │
│  ┌─────────────────────────────┐   │
│  │   Module Registry           │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐│   │
│  │  │Menu  │ │Prem. │ │Energy││   │
│  │  └──────┘ └──────┘ └──────┘│   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │      Core Infrastructure    │   │
│  │  - BaseModule               │   │
│  │  - MessageFormatter         │   │
│  │  - StateManager             │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│         REST API Layer              │
│  /api/health                        │
│  /api/modules                       │
│  /api/orders                        │
│  /api/premium                       │
│  /api/wallet                        │
└─────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│       External Services             │
│  - Admin Panel                      │
│  - Monitoring                       │
│  - Analytics                        │
└─────────────────────────────────────┘
```

## 模块开发指南

### 创建新模块

1. 继承 `BaseModule`:

```python
from src.core.base import BaseModule
from src.core.formatter import MessageFormatter
from src.core.state_manager import ModuleStateManager

class MyModule(BaseModule):
    def __init__(self):
        self.formatter = MessageFormatter()
        self.state_manager = ModuleStateManager()
    
    @property
    def module_name(self) -> str:
        return "my_module"
    
    def get_handlers(self) -> List[BaseHandler]:
        return [
            CommandHandler("mycommand", self.handle_command)
        ]
```

2. 注册模块:

```python
from src.core.registry import get_registry

registry = get_registry()
registry.register(
    MyModule(),
    priority=5,
    enabled=True
)
```

## API使用示例

### Python客户端

```python
import requests

API_KEY = "your-api-key"
BASE_URL = "http://localhost:8001/api"

headers = {"X-API-Key": API_KEY}

# 获取系统统计
response = requests.get(f"{BASE_URL}/stats", headers=headers)
stats = response.json()

# 创建订单
order_data = {
    "user_id": 123456,
    "base_amount": 10.0,
    "order_type": "premium"
}
response = requests.post(
    f"{BASE_URL}/orders", 
    json=order_data,
    headers=headers
)
order = response.json()

# 发送消息
message_data = {
    "user_id": 123456,
    "message": "Hello from API!",
    "parse_mode": "HTML"
}
response = requests.post(
    f"{BASE_URL}/message/send",
    json=message_data,
    headers=headers
)
```

### JavaScript客户端

```javascript
const API_KEY = 'your-api-key';
const BASE_URL = 'http://localhost:8001/api';

// 获取模块列表
fetch(`${BASE_URL}/modules`, {
    headers: {
        'X-API-Key': API_KEY
    }
})
.then(res => res.json())
.then(data => console.log(data));

// 检查Premium资格
fetch(`${BASE_URL}/premium/check-eligibility`, {
    method: 'POST',
    headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        user_id: 123456
    })
})
.then(res => res.json())
.then(data => console.log(data));
```

## 迁移指南

### 从旧版本迁移

1. **备份数据**
   ```bash
   cp -r data/ data_backup/
   ```

2. **更新配置**
   - 添加 `API_HOST` 和 `API_PORT` 到 `.env`
   - 配置 `API_KEYS`（可选）

3. **测试新版本**
   ```bash
   python -m src.bot_v2
   ```

4. **验证功能**
   - 测试Premium功能
   - 测试主菜单
   - 测试API接口

5. **切换生产**
   - 停止旧版本
   - 启动新版本
   - 监控日志

## 故障排除

### Bot不响应
1. 检查Token配置
2. 查看日志文件
3. 验证网络连接

### API无法访问
1. 检查端口是否被占用
2. 验证防火墙设置
3. 查看API日志

### 模块加载失败
1. 检查模块依赖
2. 查看错误日志
3. 验证模块注册

## 监控和维护

### 健康检查

```bash
# 检查Bot健康状态
curl http://localhost:8001/api/health

# 检查详细统计
curl -H "X-API-Key: your-key" http://localhost:8001/api/stats
```

### 日志查看

```bash
# 查看Bot日志
tail -f logs/bot.log

# 查看API日志
tail -f logs/api.log
```

### 性能监控

- CPU使用率: `< 20%`
- 内存使用: `< 500MB`
- 响应时间: `< 1s`
- 错误率: `< 0.1%`

## Services 层与 Legacy 目录

### Legacy 目录 (`src/legacy/`)

存放 V1 版本的旧版业务逻辑实现，仅用于向后兼容。

**目录结构**:
```
src/legacy/
├── __init__.py
├── energy/           # 能量服务旧版实现
│   ├── manager.py    - 能量订单管理器
│   ├── client.py     - API 客户端
│   └── models.py     - 数据模型
├── trx_exchange/     # TRX 兑换旧版实现
│   ├── config.py     - 兑换配置
│   ├── rate_manager.py - 汇率管理
│   └── trx_sender.py - TRX 发送器
└── address_query/    # 地址查询旧版实现
    ├── validator.py  - 地址验证
    └── explorer.py   - 浏览器链接
```

**使用规则**:
- 不在 legacy 目录新增业务代码
- 新代码应使用 services 层
- 逐步将调用方迁移到 services 层

### Services 层 (`src/services/`)

提供纯业务逻辑服务接口，供 modules/ 和 api/ 调用。
服务层不依赖 Telegram 类型，只接受业务参数，返回业务结果。

**目录结构**:
```
src/services/
├── __init__.py
├── payment_service.py   # 支付相关操作
├── wallet_service.py    # 钱包余额管理
├── energy_service.py    # 能量服务操作
├── trx_service.py       # TRX 兑换操作
├── address_service.py   # 地址验证和查询
└── config_service.py    # 配置管理
```

**各服务职责**:

| 服务 | 职责 |
|------|------|
| PaymentService | 唯一金额生成、订单创建、支付确认 |
| WalletService | 余额查询、增减、检查 |
| EnergyService | 能量套餐、订单创建、状态更新 |
| TRXService | 汇率管理、TRX 兑换、发送 |
| AddressService | 地址验证、限频检查、浏览器链接 |
| ConfigService | 配置读写、价格管理 |

**使用示例**:
```python
from src.services import AddressService, EnergyService

# 验证地址
address_service = AddressService()
is_valid, error = address_service.validate_address("TXxxxx...")

# 创建能量订单
energy_service = EnergyService()
order, error = energy_service.create_order(
    user_id=12345,
    order_type=EnergyOrderType.HOURLY,
    receive_address="TXxxxx...",
    energy_amount=65000
)
```

---

## 更新日志

### v2.1.0 (2025-11-26)
- ✨ 新增 `src/legacy/` 目录，存放旧版业务逻辑
- ✨ 新增 `src/services/` 层，提供业务服务接口
- 🔄 更新各模块 import，指向 legacy
- 📝 更新架构文档
- 🔧 补充缺失的模块文件（menu/states.py, menu/keyboards.py, address_query/keyboards.py）
- 🔧 统一回调数据命名（premium_, addrq_ 前缀）

### v2.0.0 (2024-11-24)
- ✨ 新增标准化模块系统
- ✨ 新增REST API接口
- 🐛 修复Premium Markdown错误
- 🐛 修复主菜单重复提示
- ⚡ 优化模块加载性能
- 📝 完善文档和测试
