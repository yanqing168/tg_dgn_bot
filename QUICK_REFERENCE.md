# 🚀 快速参考指南

> 运维/开发速查表  
> 版本: v4.0  
> 更新: 2025-11-26  

---

## 📍 当前状态

| 项目 | 状态 | 说明 |
|------|------|------|
| **Bot运行** | ✅ 稳定 | V2 架构已落地 |
| **测试** | ✅ 全绿 | 430 passed, 0 failed |
| **数据库** | ✅ 统一 | 唯一生产库 tg_bot.db |
| **入口** | ✅ V2 | `python -m src.bot_v2` |

---

## 🎯 常用命令

### 启动 Bot
```bash
# 启动 V2 版本（推荐）
python -m src.bot_v2

# 或启动旧版本
python -m src.bot
```

### 运行测试
```bash
# 全量测试
pytest

# 快速测试（简洁输出）
pytest --tb=line -q

# 单个模块测试
pytest tests/test_premium_v2_integration.py -v

# 带覆盖率
pytest --cov=src tests/
```

### 数据库
```bash
# 数据库迁移
alembic upgrade head

# 查看当前版本
alembic current
```

---

## 📂 关键路径速查

### 🔴 核心入口

| 文件 | 用途 |
|------|------|
| `src/bot_v2.py` | **V2 主入口（推荐）** |
| `src/bot.py` | V1 入口（兼容） |
| `tg_bot.db` | 唯一生产数据库 |

### 🟡 分层目录

| 目录 | 职责 |
|------|------|
| `src/core/` | 模块基类、注册中心、状态管理 |
| `src/common/` | NavigationManager、SafeConversationHandler |
| `src/modules/` | 标准化业务模块（Premium/Energy/...） |
| `src/services/` | 业务逻辑服务层 |
| `src/tasks/` | 定时任务（订单过期等） |
| `src/legacy/` | 旧实现（只读归档） |

### 🟢 关键文件

| 文件 | 说明 |
|------|------|
| `src/common/navigation_manager.py` | 统一导航管理 |
| `src/common/conversation_wrapper.py` | 安全对话包装 |
| `src/premium/handler_v2.py` | Premium V2 处理器 |
| `tests/conftest.py` | 测试 fixture（bot_app_v2）|
| `docs/AGENT_RULES.md` | AI 修改规则 |

---

## 🛠️ 常用命令

### 开发命令
```bash
# 安装依赖
make install

# 运行测试
make test

# 格式化代码
make format

# 代码检查
make lint
```

### 部署命令
```bash
# Docker部署
make docker

# 数据库迁移
make migrate

# 清理缓存
make clean
```

### Bot管理
```bash
# 启动Bot（当前版本）
python -m src.bot

# 启动Bot（新架构）
python -m presentation.main

# 查看日志
tail -f bot.log

# 检查状态
grep ERROR bot.log | tail -20
```

---

## 📊 架构对比

### 当前架构（v2.2）
```
src/
├── premium/       # Premium功能
├── wallet/        # 钱包功能
├── energy/        # 能量功能
├── common/        # 公共模块
└── bot.py        # 主入口
```

### 目标架构（v3.0）
```
domain/           # 业务核心
application/      # 应用逻辑
infrastructure/   # 技术实现
presentation/     # 用户接口
```

---

## 📈 迁移进度

| 阶段 | 任务 | 状态 | 预计时间 |
|------|------|------|----------|
| **Phase 1** | 代码重构 | 🔄 待开始 | 1周 |
| **Phase 2** | 基础设施 | ⏳ 待定 | 1周 |
| **Phase 3** | 中间件 | ⏳ 待定 | 1周 |
| **Phase 4** | 部署 | ⏳ 待定 | 3天 |

---

## 🔍 问题诊断

### Bot无法启动
```bash
# 检查Python进程
tasklist | findstr python

# 停止所有进程
taskkill /IM python.exe /F

# 重新启动
python -m src.bot
```

### 数据库连接失败
```bash
# 检查PostgreSQL
docker ps | grep postgres

# 查看日志
docker logs tg_bot_postgres

# 重启数据库
docker-compose -f docker-compose.prod.yml restart postgres
```

### 内存占用过高
```bash
# 查看内存
wmic process where name="python.exe" get WorkingSetSize

# 重启Bot
taskkill /PID <pid> /F
python -m src.bot
```

---

## 📚 文档链接

### 架构文档
- [生产架构路线图](PRODUCTION_ARCHITECTURE_ROADMAP.md)
- [文档更新计划](DOCUMENTATION_UPDATE_PLAN.md)
- [修复完成报告](PRODUCTION_FIX_COMPLETED_20241124.md)

### 操作文档
- [部署指南](docs/deployment/DEPLOYMENT.md)
- [监控配置](docs/operations/MONITORING.md)
- [故障处理](docs/operations/TROUBLESHOOTING.md)

### 开发文档
- [贡献指南](docs/development/CONTRIBUTING.md)
- [测试指南](docs/development/TESTING_GUIDE.md)
- [API文档](docs/api/API_DOCUMENTATION.md)

---

## 💡 最佳实践

### 迁移建议
1. **先迁移无状态服务** - 从简单的开始
2. **保持向后兼容** - 新旧代码并存
3. **充分测试** - 每个模块都要测试
4. **逐步切换** - 灰度发布

### 性能优化
1. **使用Redis缓存** - 减少数据库访问
2. **异步处理** - 提高并发能力
3. **连接池** - 复用数据库连接
4. **监控指标** - 及时发现问题

### 安全建议
1. **环境变量** - 不要硬编码密钥
2. **最小权限** - 数据库用户权限
3. **日志脱敏** - 不记录敏感信息
4. **定期备份** - 数据安全第一

---

## 🆘 紧急联系

### 问题升级路径
1. 查看日志 → 2. 查阅文档 → 3. 运行诊断 → 4. 联系团队

### 回滚方案
```bash
# 从备份恢复
cp -r backups/backup_YYYYMMDD_HHMMSS/* .

# 重启旧版本
python -m src.bot
```

---

## 🔒 安全加固 (2025-11-26)

| 编号 | 加固项 | 文件 |
|------|--------|------|
| H2 | 订单回调 user_id 校验 | `src/trx_exchange/handler.py` |
| H2 | 管理员回调 owner 校验 | `src/orders/query_handler.py` |
| M2 | API 日志脱敏 | `src/energy/client.py` |
| M5 | 钱包扣费事务 rollback | `src/wallet/wallet_manager.py` |
| L2 | 后缀分配重试限制 | `src/payments/order.py` |

---

## ✅ 检查清单

### 每日检查
- [ ] Bot运行状态
- [ ] 错误日志
- [ ] 数据库连接
- [ ] 内存使用

### 每周检查
- [ ] 备份数据
- [ ] 更新文档
- [ ] 性能分析
- [ ] 安全审计

### 发布前检查
- [ ] 所有测试通过
- [ ] 文档已更新
- [ ] 备份已创建
- [ ] 回滚方案就绪

---

*快速参考版本: 1.1*  
*最后更新: 2025-11-26*  
*下次审查: 2025-12-03*
