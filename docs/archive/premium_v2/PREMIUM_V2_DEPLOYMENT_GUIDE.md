# Premium V2 功能部署指南

## 📋 功能概述

Premium V2 是对原有 Premium 会员功能的全面升级，主要改进包括：
- 支持给自己/他人开通选择
- 实时用户身份验证
- 完善的安全机制
- 更好的用户体验

## 🚀 部署步骤

### 1. 数据库迁移

运行以下命令执行数据库迁移：

```bash
# 备份现有数据库
python scripts/backup_dbs.py

# 执行数据库迁移
alembic upgrade head
```

新增的数据表：
- `user_bindings` - 用户绑定表（存储用户名与user_id映射）
- `premium_orders` - Premium专用订单表

### 2. 更新配置

确保以下配置项正确设置：

```python
# .env 文件
BOT_TOKEN=your_bot_token
USDT_TRC20_RECEIVE_ADDR=your_receive_address
ORDER_TIMEOUT_MINUTES=30  # 订单超时时间
```

### 3. 代码部署

新增/修改的主要文件：
- `src/premium/handler_v2.py` - 新的Premium处理器
- `src/premium/user_verification.py` - 用户验证服务
- `src/premium/security.py` - 安全机制
- `src/database.py` - 新增数据模型
- `migrations/versions/003_user_bindings.py` - 数据库迁移脚本

### 4. 功能测试

运行测试确保所有功能正常：

```bash
# 运行完整测试套件
python tests/test_premium_complete_ci.py

# 单独测试各模块
python tests/test_user_verification.py
python tests/test_premium_security.py
python tests/test_premium_v2_integration.py
```

## 📱 用户使用流程

### 给自己开通 Premium

1. 用户点击"💎 Premium会员"
2. 选择"💎 给自己开通"
3. 系统显示用户信息（用户名、昵称）
4. 选择套餐时长（3/6/12个月）
5. 确认订单并支付
6. 支付成功后自动发放

### 给他人开通 Premium

1. 用户点击"💎 Premium会员"
2. 选择"🎁 给他人开通"
3. 输入对方用户名
4. 系统验证用户是否存在
   - 如存在：显示用户信息
   - 如不存在：提示用户先与Bot交互
5. 选择套餐时长
6. 确认订单并支付
7. 支付成功后自动发放给对方

## 🔒 安全特性

### 1. 用户限额控制
- 每用户每天最多购买 5 次
- 两次购买至少间隔 1 分钟
- 每个收件人每天最多接收 3 次

### 2. 黑名单机制
- 支持动态添加/移除黑名单用户
- 黑名单用户无法购买Premium

### 3. 异常行为检测
- 监控异常购买模式
- 风险评分系统（0-100）
- 高风险订单自动拦截

### 4. 用户身份验证
- 实时验证用户存在性
- 防止为不存在的用户付费
- 用户绑定机制确保身份准确

## 🔄 回滚方案

如需回滚到旧版本：

1. 恢复数据库备份：
```bash
# 恢复备份
cp backup_db/bot_db_[timestamp].sqlite data/bot_db.sqlite
```

2. 切换代码分支：
```bash
git checkout [previous-version-tag]
```

3. 修改bot.py导入：
```python
# 改回旧版handler
from .premium.handler import PremiumHandler  # 而不是 handler_v2
```

## 📊 监控指标

建议监控以下指标：
- 每日Premium订单数量
- 用户验证失败率
- 安全拦截次数
- 订单完成率
- 平均处理时间

## ⚠️ 注意事项

1. **首次部署**：
   - 确保数据库迁移成功执行
   - 验证bot用户名正确配置

2. **用户绑定**：
   - 用户首次与bot交互时自动绑定
   - 已有用户需要重新交互以建立绑定

3. **兼容性**：
   - 新系统向后兼容旧订单数据
   - 不影响其他功能模块

## 🆘 故障排查

### 问题：用户验证总是失败
- 检查user_bindings表是否有数据
- 确认用户是否与bot交互过
- 查看日志中的验证错误信息

### 问题：订单创建失败
- 检查数据库连接
- 验证USDT接收地址配置
- 查看订单管理器日志

### 问题：安全限制过于严格
- 调整`src/premium/security.py`中的配置参数
- 查看风险评分详情
- 考虑将正常用户移出黑名单

## 📞 支持

如有问题，请查看：
- 日志文件：`logs/bot.log`
- 测试报告：`tests/test_premium_complete_ci.py`
- 文档：`docs/`目录下的相关文档

---

*更新日期：2024-11-24*
*版本：Premium V2.0*
