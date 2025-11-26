# 支付方式架构文档

## 概述

Bot 支持三种支付方式，适用于不同业务场景：

| 功能类型 | 支付方式 | 金额格式 | 实现方法 |
|---------|---------|---------|---------|
| 💎 Premium直充 | 固定地址+后缀 | 9.587 USDT | 现有系统 |
| 💰 余额充值 | 固定地址+后缀 | 50.123 USDT | 现有系统 |
| 🔍 地址查询 | **免费功能** | 无需支付 | 限频机制 |

| ⚡️ 能量闪租 | 代理地址（TRX支付） | 3/6/30 TRX | **新增功能** |

| 🔥 笔数套餐 | 代理地址（USDT支付） | 5/10/20 USDT | **新增功能** |

| 🔄 闪兑 | 代理地址（USDT支付） | 10/20/50 USDT | **新增功能** |

---

## 1. 三位小数后缀支付系统

### 适用场景

- Premium 会员直充
- Bot 余额充值

### 工作原理

```text
用户支付: 基础金额 + 0.001-0.999 = 最终金额
示例: 9.000 + 0.587 = 9.587 USDT

```text

### 优势

- ✅ 订单唯一标识（999个并发）
- ✅ 幂等性保证

- ✅ 无需数据库即可识别订单
- ✅ TRC20 回调自动处理

### 实现文件

- `src/payments/amount_calculator.py` - 后缀计算
- `src/payments/suffix_manager.py` - 后缀池管理（Redis）

- `src/payments/trc20_handler.py` - TRC20 回调处理

---

## 2. TRX/USDT 直转模式

### 适用场景

- 能量闪租（时长能量）
- 笔数套餐

- 闪兑

### 工作原理

```text
用户 → 代理地址（整数金额）→ 代理后台自动处理

```text

### 三种代理地址配置

#### 2.1 能量闪租地址（收 TRX）

```bash
ENERGY_RENT_ADDRESS=TYourEnergyRentAddress

```text

**特点：**

- 用户转账 **TRX**（不是 USDT）
- 整数金额（3/6/30/60 TRX）

- 6秒自动到账
- 1小时有效期

**价格体系：**
| 套餐 | 单价 | 示例 |
|-----|------|------|
| 6.5万能量 | 3 TRX | 5笔 = 15 TRX |
| 13.1万能量 | 6 TRX | 5笔 = 30 TRX |

**代理后台配置：**
1. 登录 trxno.com 代理后台
2. 找到"能量租用地址"设置
3. 填入你的 TRX 收款地址
4. 设置价格和笔数限制（1-20笔）

#### 2.2 笔数套餐地址（收 USDT）

```bash
ENERGY_PACKAGE_ADDRESS=TYourPackageAddress

```text

**特点：**

- 用户转账 **USDT TRC20**
- 整数金额（最低 5 USDT）

- 弹性扣费：有U扣1笔，无U扣2笔
- 每天至少使用一次

**价格说明：**

- 每笔价格：约 0.5 USDT
- 5 USDT ≈ 10笔

- 10 USDT ≈ 20笔

**代理后台配置：**
1. 登录 trxno.com 代理后台
2. 找到"笔数套餐地址"设置
3. 填入你的 USDT 收款地址

#### 2.3 闪兑地址（收 USDT）

```bash
ENERGY_FLASH_ADDRESS=TYourFlashExchangeAddr

```text

**特点：**

- 用户转账 **USDT TRC20**
- 整数金额（自定义）

- USDT 直接兑换能量
- 即时到账

**代理后台配置：**
1. 登录 trxno.com 代理后台
2. 找到"闪兑地址"设置
3. 填入你的 USDT 收款地址

---

## 3. 地址查询（免费功能）

### 特点

- ✅ **完全免费**，无需支付
- ✅ 限频机制：管理员可在后台配置（默认每用户 30 分钟 1 次）
- ✅ SQLite 持久化存储
- ✅ 重启后限频仍生效

### 实现文件

- `src/address_query/handler.py` - 查询处理器
- `src/address_query/rate_limit.py` - 限频管理

- `src/database/models.py` - AddressQueryLog 模型

### 配置

```bash
ADDRESS_QUERY_RATE_LIMIT_MINUTES=30  # 限频时间（分钟）

```text

---

## 4. 资金流和利润分析

### 能量闪租（TRX 直转）

```text
用户 → 代理地址（30 TRX）→ trxno.com 后台自动扣费（25 TRX）→ 利润（5 TRX）

```text

**收益：**

- 用户支付：30 TRX
- 代理成本：25 TRX

- Bot 拥有者利润：5 TRX（20%）

### 笔数套餐（USDT 直转）

```text
用户 → 代理地址（10 USDT）→ 自动充值到用户账号

```text

**说明：**

- 用户支付 USDT 直接充值到代理后台
- 按笔扣费（有U扣1笔，无U扣2笔）

- Bot 拥有者赚取差价

---

## 5. 用户流程对比

### 5.1 Premium 直充（后缀模式）

```text
1. 用户点击"飞机会员"
2. 选择套餐（3/6/12个月）
3. 输入接收人（@username）
4. 显示支付金额（9.587 USDT）
5. 转账到固定地址
6. TRC20回调自动交付

```text

### 5.2 能量闪租（直转模式）

```text
1. 用户点击"能量闪租"
2. 选择套餐（6.5万/13.1万）
3. 输入购买笔数（1-20）
4. 输入接收地址
5. 显示支付信息（代理TRX地址 + 整数金额）
6. 用户转账（如：30 TRX）
7. 6秒自动到账

```text

### 5.3 地址查询（免费）

```text
1. 用户点击"地址监听"
2. 检查限频（30分钟1次）
3. 输入波场地址
4. 显示余额和交易记录
5. 提供区块链浏览器链接

```text

---

## 6. 配置文件示例

### .env

```bash

# USDT TRC20 Payment (Premium + 余额充值)

USDT_TRC20_RECEIVE_ADDR=TYourUSDTReceiveAddress

# Energy Proxy Addresses (TRX Direct Transfer)

ENERGY_RENT_ADDRESS=TYourEnergyRentAddress      # 时长能量收TRX地址

ENERGY_PACKAGE_ADDRESS=TYourPackageAddress      # 笔数套餐收USDT地址

ENERGY_FLASH_ADDRESS=TYourFlashExchangeAddr     # 闪兑收USDT地址

# Energy API Configuration

ENERGY_API_USERNAME=your_trxno_username
ENERGY_API_PASSWORD=your_trxno_password
ENERGY_API_BASE_URL=https://trxno.com
ENERGY_API_BACKUP_URL=https://trxfast.com

# Address Query Rate Limit

ADDRESS_QUERY_RATE_LIMIT_MINUTES=30

```text

---

## 7. 技术架构

### 文件结构

```text
src/
├── payments/                    # 支付系统（后缀模式）

│   ├── amount_calculator.py    # 三位小数后缀计算

│   ├── suffix_manager.py       # 后缀池管理（Redis）

│   ├── trc20_handler.py        # TRC20 回调处理

│   └── order.py                # 订单管理

│
├── energy/                      # 能量服务（直转模式）

│   ├── handler_direct.py       # 直转模式处理器 ✨ 新增

│   ├── models.py               # 数据模型

│   └── client.py               # API客户端

│
├── address_query/               # 地址查询（免费）

│   ├── handler.py              # 查询处理器

│   ├── validator.py            # 地址验证

│   ├── explorer.py             # 区块链浏览器链接

│   └── rate_limit.py           # 限频管理

│
├── wallet/                      # 钱包系统

│   ├── wallet_manager.py       # 余额管理

│   └── profile_handler.py      # 个人中心

│
└── premium/                     # Premium服务

    ├── handler.py              # Premium处理器

    └── delivery.py             # 自动交付

```text

---

## 8. 测试覆盖

### 已测试功能

- ✅ 三位小数后缀计算（10/10）
- ✅ 后缀池管理（12/12 Redis集成）

- ✅ TRC20 回调处理（15/15）
- ✅ Premium 交付（8/8）

- ✅ 钱包管理（16/16）
- ✅ 地址查询限频（9/9）

- ✅ 地址验证（8/8）

### 待测试功能

- 📋 能量直转模式处理器
- 📋 代理地址配置验证

- 📋 TRX/USDT 支付流程

---

## 9. 常见问题

### Q1: 为什么能量闪租用 TRX，笔数套餐用 USDT？

**A:** 这是 trxno.com 代理平台的规则：

- 时长能量（闪租）: 用户转 TRX → 后台自动购买能量
- 笔数套餐: 用户转 USDT → 充值到用户账号

### Q2: 地址查询为什么免费？

**A:** 地址查询是基础服务，限频机制已足够防止滥用，无需收费。

### Q3: 如何防止用户转错金额？

**A:** 

- **后缀模式**: 后缀唯一性保证，转错金额无法匹配订单
- **直转模式**: 用户界面明确提示"整数金额"，代理后台自动识别

### Q4: 代理后台如何识别用户地址？

**A:** 

- 能量闪租: 用户先输入接收地址 → 转账 → 后台根据金额自动处理
- 笔数套餐/闪兑: 同上流程

### Q5: 利润如何赚取？

**A:**

- **Premium**: 你设定的价格（如 $10/月） - 官方 Premium 成本
- **能量闪租**: 用户支付（如 30 TRX） - 代理后台扣费（如 25 TRX） = 利润

- **笔数套餐**: 用户充值金额 - 实际消耗 = 利润

---

## 10. 部署检查清单

### 环境变量配置

- [ ] `USDT_TRC20_RECEIVE_ADDR` - Premium/余额充值地址
- [ ] `ENERGY_RENT_ADDRESS` - 能量闪租地址（收TRX）

- [ ] `ENERGY_PACKAGE_ADDRESS` - 笔数套餐地址（收USDT）
- [ ] `ENERGY_FLASH_ADDRESS` - 闪兑地址（收USDT）

- [ ] `ENERGY_API_USERNAME` - trxno.com 用户名
- [ ] `ENERGY_API_PASSWORD` - trxno.com 密码

### 代理后台配置

- [ ] trxno.com 账户已创建
- [ ] 能量租用地址已设置

- [ ] 笔数套餐地址已设置
- [ ] 闪兑地址已设置

- [ ] 价格和限制已配置

### 功能测试

- [ ] Premium 直充流程测试
- [ ] 余额充值流程测试

- [ ] 地址查询限频测试
- [ ] 能量闪租 TRX 转账测试

- [ ] 笔数套餐 USDT 转账测试
- [ ] 闪兑流程测试

---

## 11. 维护建议

### 日常监控

1. **Redis 后缀池**: 定期检查可用后缀数量
2. **代理余额**: 确保 trxno.com 账户有足够余额
3. **订单状态**: 监控订单成功率和失败原因
4. **限频日志**: 检查地址查询滥用情况

### 故障处理

- **后缀耗尽**: 扩大后缀范围或增加过期时间
- **代理余额不足**: 及时充值 TRX/USDT

- **TRC20 回调失败**: 检查签名验证和网络连接
- **能量未到账**: 联系 trxno.com 客服

---

## 12. 技术联系

- **代理平台**: trxno.com / trxfast.com

- **API 文档**: 联系代理平台获取
- **技术支持**: 参考 AGENTS.md Issue #1-4
