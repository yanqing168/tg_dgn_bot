# 🔧 地址查询API问题修复方案

**问题**: 输入地址后显示"API暂时不可用"

**时间**: 2025-11-26 05:15

---

## 🔍 问题分析

### 当前代码问题

**文件**: `src/modules/address_query/handler.py`

#### 问题1: 数据库字段名错误 🔴

**位置**: 第311行

```python
last_query = db.query(AddressQueryLog).filter_by(
    user_id=user_id
).order_by(AddressQueryLog.query_time.desc()).first()  # ❌ 错误：query_time
```

**数据库实际字段**: `last_query_at`

**错误**: 使用了不存在的字段`query_time`，应该是`last_query_at`

#### 问题2: TronGrid API可能返回401或其他错误

**位置**: 第380-384行

```python
response = await client.get(account_url, headers=headers)

if response.status_code != 200:
    logger.warning(f"TronGrid API返回错误: {response.status_code}")
    return None  # 直接返回None，导致显示"API暂时不可用"
```

---

## 🔧 详细修复方案

### 修复1: 更正数据库字段名 ✅

**文件**: `src/modules/address_query/handler.py`

**修改位置**: 第311行和第314行

```python
# 修改前
last_query = db.query(AddressQueryLog).filter_by(
    user_id=user_id
).order_by(AddressQueryLog.query_time.desc()).first()  # ❌

if last_query:
    time_since_last = datetime.now() - last_query.query_time  # ❌

# 修改后
last_query = db.query(AddressQueryLog).filter_by(
    user_id=user_id
).order_by(AddressQueryLog.last_query_at.desc()).first()  # ✅

if last_query:
    time_since_last = datetime.now() - last_query.last_query_at  # ✅
```

### 修复2: 改进TronGrid API错误处理 ✅

**文件**: `src/modules/address_query/handler.py`

**修改位置**: 第375-434行

```python
async def _fetch_address_info(self, address: str) -> Optional[Dict]:
    """
    获取地址信息（使用TronGrid API）
    
    Args:
        address: TRON地址
        
    Returns:
        地址信息字典或None
    """
    try:
        import httpx
        from src.config import settings
        
        logger.info(f"尝试获取地址信息: {address}")
        
        # 使用TronGrid API获取真实数据
        api_url = getattr(settings, 'tron_api_url', 'https://api.trongrid.io')
        api_key = getattr(settings, 'tron_api_key', None)
        
        headers = {
            'Accept': 'application/json'
        }
        
        # 尝试使用API密钥
        use_api_key = api_key and api_key.strip()
        if use_api_key:
            headers['TRON-PRO-API-KEY'] = api_key.strip()
            logger.info(f"使用API密钥请求: {api_key[:10]}...")
        else:
            logger.info("使用公共API（无密钥）")
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 获取账户信息
            account_url = f"{api_url}/v1/accounts/{address}"
            logger.info(f"请求TronGrid API: {account_url}")
            
            response = await client.get(account_url, headers=headers)
            
            # 如果401且使用了密钥，尝试不使用密钥（降级到公共API）
            if response.status_code == 401 and use_api_key:
                logger.warning(f"API密钥无效(401)，尝试使用公共API")
                headers.pop('TRON-PRO-API-KEY', None)
                response = await client.get(account_url, headers=headers)
            
            # 如果仍然不是200，记录详细错误并返回None
            if response.status_code != 200:
                logger.error(
                    f"TronGrid API请求失败: "
                    f"状态码={response.status_code}, "
                    f"URL={account_url}, "
                    f"响应={response.text[:500]}"
                )
                return None
            
            data = response.json()
            logger.debug(f"API响应数据: {data}")
            
            # 解析账户信息
            account_data = data.get('data', [{}])[0] if data.get('data') else {}
            
            if not account_data:
                logger.warning(f"API返回空数据: {data}")
                # 即使没有数据，也返回零余额，而不是None
                return {
                    'trx_balance': '0.00',
                    'usdt_balance': '0.00',
                    'recent_txs': []
                }
            
            # 获取TRX余额（sun转换为TRX）
            trx_balance_sun = account_data.get('balance', 0)
            trx_balance = trx_balance_sun / 1_000_000  # 1 TRX = 1,000,000 sun
            
            # 获取USDT余额（TRC20）
            usdt_balance = 0
            trc20_tokens = account_data.get('trc20', [])
            for token in trc20_tokens:
                # USDT合约地址: TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
                if 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t' in str(token):
                    token_value = token.get(list(token.keys())[0], 0)
                    usdt_balance = token_value / 1_000_000  # USDT也是6位小数
                    break
            
            # 获取最近交易（简化版）
            recent_txs = []
            try:
                tx_url = f"{api_url}/v1/accounts/{address}/transactions"
                tx_response = await client.get(tx_url, headers=headers, params={'limit': 5})
                if tx_response.status_code == 200:
                    tx_data = tx_response.json()
                    transactions = tx_data.get('data', [])
                    
                    for tx in transactions[:5]:
                        # 简化交易信息
                        tx_info = {
                            'direction': '转入' if tx.get('to_address') == address else '转出',
                            'amount': '0',
                            'token': 'TRX',
                            'hash': tx.get('txID', '')[:10],
                            'time': tx.get('block_timestamp', '')
                        }
                        recent_txs.append(tx_info)
                else:
                    logger.warning(f"获取交易历史失败: {tx_response.status_code}")
            except Exception as tx_error:
                logger.warning(f"获取交易历史异常: {tx_error}")
            
            result = {
                'trx_balance': f"{trx_balance:.2f}",
                'usdt_balance': f"{usdt_balance:.2f}",
                'recent_txs': recent_txs
            }
            
            logger.info(f"成功获取地址信息: TRX={result['trx_balance']}, USDT={result['usdt_balance']}, 交易数={len(recent_txs)}")
            return result
    
    except httpx.TimeoutException as e:
        logger.error(f"API请求超时: {e}")
        return None
    except httpx.RequestError as e:
        logger.error(f"API请求错误: {e}")
        return None
    except Exception as e:
        logger.error(f"获取地址信息失败: {e}", exc_info=True)
        return None
```

### 修复3: 改进错误消息 ✅

**文件**: `src/modules/address_query/messages.py`

添加更详细的错误消息：

```python
# 在messages.py中添加
QUERY_RESULT_NO_API = """
🔍 <b>地址查询结果</b>

📍 <b>地址</b>: <code>{address}</code>

⚠️ <b>提示</b>: API暂时不可用，无法获取余额信息

💡 <b>建议</b>:
• 请稍后重试
• 或使用下方链接在区块浏览器中查看
"""
```

---

## 📝 完整修复步骤

### 步骤1: 修复数据库字段名

```python
# 文件: src/modules/address_query/handler.py
# 第311行和第314行

# 修改 _check_rate_limit 方法
def _check_rate_limit(self, user_id: int) -> tuple[bool, int]:
    """检查用户查询限频"""
    try:
        db = SessionLocal()
        cooldown_minutes = get_address_cooldown_minutes()
        
        # 查询最近一次查询记录
        last_query = db.query(AddressQueryLog).filter_by(
            user_id=user_id
        ).order_by(AddressQueryLog.last_query_at.desc()).first()  # ✅ 修复
        
        if last_query:
            time_since_last = datetime.now() - last_query.last_query_at  # ✅ 修复
            if time_since_last < timedelta(minutes=cooldown_minutes):
                remaining = cooldown_minutes - int(time_since_last.total_seconds() / 60)
                return False, max(1, remaining)
        
        return True, 0
        
    except Exception as e:
        logger.error(f"检查限频失败: {e}", exc_info=True)
        return True, 0  # 出错时允许查询
    finally:
        db.close()
```

### 步骤2: 替换整个 _fetch_address_info 方法

使用上面"修复2"中的完整代码替换现有方法。

### 步骤3: 测试修复

运行单元测试：
```bash
python -m pytest tests/test_address_query_standard.py -v
```

---

## 🧪 测试验证

### 测试场景1: 正常查询
- 输入有效地址
- 应该返回余额信息

### 测试场景2: API密钥无效
- API返回401
- 应该自动降级到公共API
- 应该返回余额信息

### 测试场景3: API完全不可用
- API返回500或超时
- 应该显示"API暂时不可用"
- 但仍提供区块浏览器链接

### 测试场景4: 空账户
- 查询从未使用过的地址
- 应该返回0余额，而不是"API不可用"

---

## 🎯 预期效果

修复后：
1. ✅ 数据库查询不会报错
2. ✅ API密钥无效时自动降级
3. ✅ 更详细的错误日志
4. ✅ 空账户返回0余额而不是错误
5. ✅ 用户体验更好

---

## ⚠️ 注意事项

1. **API密钥配置**
   - 检查 `.env` 文件中的 `TRON_API_KEY`
   - 如果密钥无效，会自动降级到公共API
   - 公共API有速率限制

2. **数据库迁移**
   - 确认 `AddressQueryLog` 表的字段名是 `last_query_at`
   - 如果不是，需要修改数据库或代码

3. **日志监控**
   - 修复后观察日志中的API请求
   - 检查是否有401错误
   - 检查降级是否成功

---

**请确认是否立即执行这些修复？** 🚀
