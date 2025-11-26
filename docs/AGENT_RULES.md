# 🤖 AI 代理修改规则

本文档定义了 AI 助手修改本项目时必须遵守的规则。

---

## 1. 架构规则

### 入口与分层
- **唯一生产入口**: `src/bot_v2.py`
- **禁止**: 新建第二套入口或并行架构

### 分层职责
| 层级 | 目录 | 职责 |
|------|------|------|
| 核心层 | `src/core/` | 模块基类、注册中心、状态管理、消息格式化 |
| 公共层 | `src/common/` | SafeConversationHandler、NavigationManager、配置、工具 |
| 模块层 | `src/modules/` | Telegram 交互（只调 service，不直接操作 DB） |
| 服务层 | `src/services/` | 业务逻辑（可调用 legacy/DB） |
| 任务层 | `src/tasks/` | 定时任务（订单过期等） |
| 遗留层 | `src/legacy/` | 旧实现归档，**禁止新增功能** |

---

## 2. 代码组织与命名

### 模块目录结构（必须包含）
```
src/modules/{module_name}/
├── handler.py      # Telegram 交互 & 状态机
├── messages.py     # 文案模板（HTML/Markdown）
├── states.py       # 状态常量（全大写枚举）
└── keyboards.py    # 按钮/键盘布局
```

### callback_data 命名规范
| 模块 | 前缀 | 示例 |
|------|------|------|
| Premium | `premium_` | `premium_self`, `premium_confirm` |
| 能量 | `energy_` | `energy_select`, `energy_cancel` |
| 地址查询 | `addrq_` | `addrq_cancel`, `addrq_back` |
| TRX 兑换 | `trx_` | `trx_confirm`, `trx_cancel` |
| 导航 | `nav_` | `nav_main_menu`, `nav_cancel` |

### 同步更新原则
修改 callback_data 或状态常量时，**必须同步更新**：
1. 对应 handler 的 pattern 匹配
2. 相关测试的断言

---

## 3. 数据库与测试约束

### 数据库
- **唯一生产库**: `tg_bot.db`（项目根目录）
- **备份库**: `backup_db/`（只作历史备份，不参与运行）

### 测试环境
- **必须**: 使用测试 DB fixture（内存/临时文件）
- **禁止**: 访问 `tg_bot.db` 生产库
- **禁止**: 连接真实 Telegram API
- **必须**: 所有被 await 的 bot 方法为 AsyncMock

### 测试 fixture
- 集成测试使用 `bot_app_v2` fixture（`tests/conftest.py`）
- 通过 `app.process_update(update)` 驱动流程

---

## 4. 工作方式

### 修改前
1. 说明本次修改目的
2. 列出将修改的文件清单
3. 确认影响范围

### 修改后
1. 更新/新增相应测试
2. 运行 `pytest` 确保全部通过
3. 更新相关文档（如有必要）

### 原则
- 一次只做一个小目标
- 不猜测，不确定时先查询代码
- 保持最小化修改

---

## 5. 禁止事项

| 禁止行为 | 原因 |
|----------|------|
| 在 handler 中直接写 SQL | 业务逻辑必须通过 services 封装 |
| 在 `src/legacy/` 中新增功能 | 遗留代码只读归档 |
| 绕开测试直接改生产逻辑 | 必须有测试保障 |
| 引入真实网络依赖 | 测试必须离线运行 |
| 修改 DB schema 不跑迁移 | 必须通过 alembic 管理 |

---

## 6. Handler 注册顺序

| Group | 用途 | 示例 |
|-------|------|------|
| 0 | 全局导航（最高优先级） | NavigationManager |
| 1 | 基础命令 | /start, /health |
| 2 | 功能模块 | Premium, Energy, TRX |
| 10 | 管理员功能 | Admin panel, Orders |
| 100 | 兜底处理器 | fallback handler |

---

*创建时间: 2025-11-26*
