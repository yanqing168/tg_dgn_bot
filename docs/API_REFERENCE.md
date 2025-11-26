# 📖 API 参考文档

## 基础信息

- **基础URL**: `http://localhost:8001/api`
- **文档URL**: `http://localhost:8001/api/docs`
- **认证方式**: API Key（Header: `X-API-Key`）

## 认证

需要认证的接口必须在请求头中包含API密钥：

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8001/api/stats
```

## 接口列表

### 系统接口

#### 健康检查
```http
GET /api/health
```

**响应示例**：
```json
{
  "status": "healthy",
  "timestamp": "2024-11-24T12:00:00",
  "modules_count": 2,
  "database": true,
  "redis": true
}
```

#### 系统统计 🔐
```http
GET /api/stats
```

**需要认证**: ✅

**响应示例**：
```json
{
  "success": true,
  "data": {
    "modules": {...},
    "orders": {...},
    "timestamp": "2024-11-24T12:00:00"
  }
}
```

### 模块管理

#### 列出所有模块
```http
GET /api/modules
```

**查询参数**：
- `enabled_only` (boolean): 只返回启用的模块

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "name": "premium",
      "enabled": true,
      "priority": 2,
      "handlers_count": 1
    }
  ]
}
```

#### 获取模块详情
```http
GET /api/modules/{module_name}
```

#### 更新模块状态 🔐
```http
PATCH /api/modules/{module_name}/status
```

**需要认证**: ✅

**请求体**：
```json
{
  "enabled": true
}
```

### Premium功能

#### 检查开通资格 🔐
```http
POST /api/premium/check-eligibility
```

**需要认证**: ✅

**请求体**：
```json
{
  "user_id": 123456
}
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "eligible": true,
    "exists": true,
    "is_verified": true,
    "binding_url": null
  }
}
```

#### 获取套餐列表
```http
GET /api/premium/packages
```

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "months": 3,
      "price": 16.0,
      "currency": "USDT",
      "discount": 0
    },
    {
      "months": 6,
      "price": 25.0,
      "currency": "USDT",
      "discount": 10
    }
  ]
}
```

### 订单管理

#### 创建订单 🔐
```http
POST /api/orders
```

**需要认证**: ✅

**请求体**：
```json
{
  "user_id": 123456,
  "base_amount": 10.0,
  "order_type": "premium",
  "recipient_id": 654321,
  "months": 3
}
```

#### 获取订单详情 🔐
```http
GET /api/orders/{order_id}
```

**需要认证**: ✅

#### 获取用户订单列表 🔐
```http
GET /api/orders/user/{user_id}
```

**需要认证**: ✅

**查询参数**：
- `status` (string): 订单状态过滤
- `limit` (int): 返回数量限制（最大100）

### 钱包功能

#### 查询余额 🔐
```http
GET /api/wallet/balance/{user_id}
```

**需要认证**: ✅

**响应示例**：
```json
{
  "user_id": 123456,
  "balance": 100.50,
  "currency": "USDT",
  "updated_at": "2024-11-24T12:00:00"
}
```

#### 增加余额 🔐
```http
POST /api/wallet/deposit
```

**需要认证**: ✅

**请求体**：
```json
{
  "user_id": 123456,
  "amount": 50.0,
  "reason": "API deposit"
}
```

### 消息功能

#### 发送消息 🔐
```http
POST /api/message/send
```

**需要认证**: ✅

**请求体**：
```json
{
  "user_id": 123456,
  "message": "Hello from API!",
  "parse_mode": "HTML",
  "disable_notification": false
}
```

#### 广播消息 🔐
```http
POST /api/message/broadcast
```

**需要认证**: ✅

**请求体**：
```json
{
  "message": "Broadcast message",
  "user_ids": [123456, 789012],
  "parse_mode": "HTML"
}
```

### 汇率功能

#### 获取USDT汇率
```http
GET /api/rates/usdt
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "base": 7.13,
    "bank": 7.15,
    "alipay": 7.14,
    "wechat": 7.13,
    "updated_at": "2024-11-24T12:00:00"
  }
}
```

### 能量功能

#### 获取能量套餐
```http
GET /api/energy/packages
```

#### 计算能量价格
```http
POST /api/energy/calculate
```

**请求体**：
```json
{
  "energy_amount": 65000
}
```

## 错误响应

所有错误响应遵循统一格式：

```json
{
  "error": "错误描述",
  "status_code": 400
}
```

### 常见错误码

| 状态码 | 描述 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权（缺少API密钥） |
| 403 | 禁止访问（API密钥无效） |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## SDK示例

### Python
```python
import requests

class BotAPIClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    def get_health(self):
        return requests.get(f"{self.base_url}/health").json()
    
    def get_modules(self):
        return requests.get(
            f"{self.base_url}/modules",
            headers=self.headers
        ).json()
    
    def create_order(self, user_id, amount):
        return requests.post(
            f"{self.base_url}/orders",
            json={"user_id": user_id, "base_amount": amount},
            headers=self.headers
        ).json()

# 使用示例
client = BotAPIClient("http://localhost:8001/api", "your-api-key")
health = client.get_health()
print(health)
```

### JavaScript/Node.js
```javascript
class BotAPIClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl;
    this.headers = { 'X-API-Key': apiKey };
  }

  async getHealth() {
    const response = await fetch(`${this.baseUrl}/health`);
    return await response.json();
  }

  async getModules() {
    const response = await fetch(`${this.baseUrl}/modules`, {
      headers: this.headers
    });
    return await response.json();
  }

  async createOrder(userId, amount) {
    const response = await fetch(`${this.baseUrl}/orders`, {
      method: 'POST',
      headers: {
        ...this.headers,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: userId,
        base_amount: amount
      })
    });
    return await response.json();
  }
}

// 使用示例
const client = new BotAPIClient('http://localhost:8001/api', 'your-api-key');
const health = await client.getHealth();
console.log(health);
```

### cURL
```bash
# 健康检查
curl http://localhost:8001/api/health

# 获取模块（需要认证）
curl -H "X-API-Key: your-api-key" \
  http://localhost:8001/api/modules

# 创建订单（需要认证）
curl -X POST \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123456, "base_amount": 10.0}' \
  http://localhost:8001/api/orders
```

## 最佳实践

1. **API密钥管理**
   - 不要在代码中硬编码API密钥
   - 使用环境变量存储密钥
   - 定期轮换密钥

2. **错误处理**
   - 始终检查响应状态码
   - 实现重试逻辑
   - 记录错误日志

3. **性能优化**
   - 使用连接池
   - 实现请求缓存
   - 批量操作优先于单个请求

4. **安全建议**
   - 生产环境使用HTTPS
   - 实施速率限制
   - 验证所有输入参数

---
*最后更新: 2024-11-24*
*API版本: 2.0.0*
