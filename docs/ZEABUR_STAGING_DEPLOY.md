# Zeabur 测试环境 Bot 部署手册（Staging）

> 生成时间：2025-11-26  
> 适用版本：Bot V2 架构

## 1. 模式判断

### 1.1 运行模式

根据 `src/bot_v2.py` 第 322-327 行：

```python
async def _run_bot(self):
    if settings.use_webhook:
        await self._start_webhook()
    else:
        await self._start_polling()
```

- **Zeabur 推荐**：Webhook 模式（`USE_WEBHOOK=true`）
- Bot 同时运行 **Telegram Bot** + **FastAPI 服务**（API 文档）

### 1.2 启动命令

Dockerfile 已明确定义：
```dockerfile
CMD ["python", "-m", "src.bot_v2"]
```

**Zeabur 推荐配置**：
- 构建方式：**使用 Dockerfile**
- 无需手动填写 Start Command

---

## 2. 环境变量清单

### 2.1 必填变量（测试环境）

| 变量名 | 用途 | Staging 建议值 |
|--------|------|----------------|
| `BOT_TOKEN` | **测试 Bot Token**（从 @BotFather 新建一个测试 Bot） | `xxxxx:STAGING_BOT_TOKEN` |
| `BOT_OWNER_ID` | 管理员 Telegram ID | 你的真实 ID |
| `USDT_TRC20_RECEIVE_ADDR` | USDT 收款地址 | 测试钱包地址 |
| `WEBHOOK_SECRET` | Webhook 签名密钥 | 随机字符串如 `staging_secret_123` |
| `USE_WEBHOOK` | 启用 Webhook 模式 | `true` |
| `BOT_WEBHOOK_URL` | Webhook 完整 URL | `https://your-staging.zeabur.app/webhook` |
| `BOT_SERVICE_PORT` | 服务端口 | `8080` |
| `DATABASE_URL` | 数据库路径 | `sqlite:///./tg_bot_staging.db` |

### 2.2 推荐变量（可选但建议设置）

| 变量名 | 用途 | Staging 建议值 |
|--------|------|----------------|
| `ENV` | 环境标识 | `staging` |
| `TZ` | 时区 | `Asia/Shanghai` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `TRX_EXCHANGE_TEST_MODE` | TRX 兑换测试模式 | `true` ⚠️ 必须 |
| `REDIS_HOST` | Redis 地址 | Zeabur Redis 服务地址 |
| `ORDER_TIMEOUT_MINUTES` | 订单超时 | `30` |

---

## 3. Zeabur 部署步骤 Checklist

### Step 1: 创建服务
- [ ] 登录 Zeabur 控制台
- [ ] 点击「从 GitHub 导入」
- [ ] 选择仓库 `tg_dgn_bot`
- [ ] 分支选择 `main`

### Step 2: 构建配置
- [ ] Zeabur 会自动检测到 Dockerfile
- [ ] 确认使用「Docker」构建方式
- [ ] 暴露端口：`8080`

### Step 3: 配置环境变量
在 Zeabur 控制台「变量」页面添加：

```
BOT_TOKEN=<你的测试Bot Token>
BOT_OWNER_ID=<你的Telegram用户ID>
USDT_TRC20_RECEIVE_ADDR=<测试收款地址>
WEBHOOK_SECRET=staging_webhook_secret_2024
USE_WEBHOOK=true
BOT_SERVICE_PORT=8080
DATABASE_URL=sqlite:///./tg_bot_staging.db
TRX_EXCHANGE_TEST_MODE=true
ENV=staging
TZ=Asia/Shanghai
```

### Step 4: 获取域名并设置 Webhook URL
- [ ] 部署完成后，获取 Zeabur 分配的域名（如 `your-app.zeabur.app`）
- [ ] 添加环境变量：
  ```
  BOT_WEBHOOK_URL=https://your-app.zeabur.app/webhook
  ```
- [ ] 重新部署使配置生效

### Step 5: 验证部署
- [ ] 查看 Zeabur 日志，确认看到：
  - `✅ Bot V2 初始化完成`
  - `✅ Bot V2 和 API 服务已启动`

---

## 4. Telegram 冒烟测试 Checklist

打开 Telegram，找到你的**测试 Bot**，按顺序执行：

### 4.1 主菜单测试
| 操作 | 预期结果 |
|------|----------|
| 发送 `/start` | 显示欢迎语 + 主菜单按钮 |
| 点击任意功能按钮 | 正常跳转，无报错 |

### 4.2 地址查询模块 ⭐ 本次修复重点
| 操作 | 预期结果 |
|------|----------|
| 点击「🔍 地址查询」 | 显示输入提示 |
| 点击「🔙 返回」按钮 | ✅ 回到主菜单（不能无响应） |

### 4.3 能量兑换模块 ⭐ 本次修复重点
| 操作 | 预期结果 |
|------|----------|
| 点击「⚡ 能量兑换」 | 显示能量菜单 |
| 点击「🔙 返回主菜单」 | ✅ 回到主菜单（不能无响应） |

### 4.4 TRX 闪兑模块 ⭐ 本次修复重点
| 操作 | 预期结果 |
|------|----------|
| 点击「🔄 TRX闪兑」 | 进入兑换流程 |
| 全流程点击 | 无报错，按钮都有响应 |

### 4.5 管理员功能（仅 Owner 可见）
| 操作 | 预期结果 |
|------|----------|
| 发送 `/admin` | 显示管理面板 |
| 发送 `/orders` | 显示订单管理 |
| 普通用户点击 | 无权限提示或无法看到 |

### 4.6 Premium 会员
| 操作 | 预期结果 |
|------|----------|
| 点击「💎 开通会员」 | 显示会员套餐选择 |
| 选择套餐 → 返回 | 正常返回主菜单 |

---

## 5. 快速验证命令

部署完成后，可用 curl 验证 API 服务：

```bash
# 健康检查（替换为你的域名）
curl https://your-app.zeabur.app/api/health
```

预期返回：`{"status": "healthy", ...}`

---

## 6. 故障排查

### 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| Bot 无响应 | Webhook URL 未设置 | 检查 `BOT_WEBHOOK_URL` |
| 数据库错误 | 路径权限问题 | 确认 `DATABASE_URL` 路径正确 |
| Redis 连接失败 | 未配置 Redis 服务 | 在 Zeabur 添加 Redis 服务并配置 `REDIS_HOST` |
| 按钮无响应 | Handler 未注册 | 查看日志确认模块加载成功 |

### 查看日志
在 Zeabur 控制台「日志」页面查看实时日志，关注：
- `❌` 开头的错误信息
- `⚠️` 开头的警告信息

---

**✅ 以上全部通过，测试环境部署成功！**
