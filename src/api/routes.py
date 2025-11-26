"""
API路由定义
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from datetime import datetime

from src.core.registry import get_registry
from src.payments.order import order_manager
from src.wallet.wallet_manager import WalletManager
from .auth import api_key_auth


logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 数据模型 ====================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: datetime
    modules_count: int
    database: bool
    redis: bool


class ModuleInfo(BaseModel):
    """模块信息"""
    name: str
    enabled: bool
    priority: int
    handlers_count: int


class ModuleStatusRequest(BaseModel):
    """模块状态请求"""
    enabled: bool


class OrderCreateRequest(BaseModel):
    """创建订单请求"""
    user_id: int
    base_amount: float
    order_type: str = "premium"
    recipient_id: Optional[int] = None
    months: Optional[int] = None


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    user_id: int
    message: str
    parse_mode: str = "HTML"
    disable_notification: bool = False


class UserBalanceResponse(BaseModel):
    """用户余额响应"""
    user_id: int
    balance: float
    currency: str = "USDT"
    updated_at: datetime


# ==================== 系统接口 ====================

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """健康检查接口"""
    from src.database import check_database_health
    
    registry = get_registry()
    stats = registry.get_statistics()
    
    try:
        db_healthy = check_database_health()
    except:
        db_healthy = False
    
    try:
        redis_healthy = order_manager.redis_client is not None
    except:
        redis_healthy = False
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        modules_count=stats['enabled_modules'],
        database=db_healthy,
        redis=redis_healthy
    )


@router.get("/stats", tags=["System"])
async def get_statistics(
    _: str = Depends(api_key_auth)
):
    """获取系统统计信息（需要认证）"""
    registry = get_registry()
    
    # 获取订单统计
    order_stats = await order_manager.get_order_statistics()
    
    # 获取模块统计
    module_stats = registry.get_statistics()
    
    return {
        "success": True,
        "data": {
            "modules": module_stats,
            "orders": order_stats,
            "timestamp": datetime.now()
        }
    }


# ==================== 模块管理接口 ====================

@router.get("/modules", tags=["Modules"])
async def list_modules(
    enabled_only: bool = Query(False, description="只返回启用的模块")
):
    """列出所有模块"""
    registry = get_registry()
    modules = []
    
    for module_name in registry.list_modules():
        info = registry.get_module_info(module_name)
        if enabled_only and not info['enabled']:
            continue
            
        modules.append(ModuleInfo(
            name=module_name,
            enabled=info['enabled'],
            priority=info['priority'],
            handlers_count=info['handlers_count']
        ))
    
    return {
        "success": True,
        "data": modules
    }


@router.get("/modules/{module_name}", tags=["Modules"])
async def get_module(module_name: str):
    """获取模块详情"""
    registry = get_registry()
    
    module = registry.get_module(module_name)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    info = registry.get_module_info(module_name)
    
    return {
        "success": True,
        "data": {
            "name": module_name,
            "enabled": info['enabled'],
            "priority": info['priority'],
            "handlers_count": info['handlers_count'],
            "metadata": info.get('metadata', {})
        }
    }


@router.patch("/modules/{module_name}/status", tags=["Modules"])
async def update_module_status(
    module_name: str,
    request: ModuleStatusRequest,
    _: str = Depends(api_key_auth)
):
    """启用或禁用模块（需要认证）"""
    registry = get_registry()
    
    if request.enabled:
        success = registry.enable_module(module_name)
    else:
        success = registry.disable_module(module_name)
    
    if not success:
        raise HTTPException(status_code=404, detail="Module not found")
    
    return {
        "success": True,
        "message": f"Module {module_name} {'enabled' if request.enabled else 'disabled'}"
    }


# ==================== Premium功能接口 ====================

@router.post("/premium/check-eligibility", tags=["Premium"])
async def check_premium_eligibility(
    user_id: int,
    _: str = Depends(api_key_auth)
):
    """检查用户是否可以开通Premium"""
    from src.premium.user_verification import get_user_verification_service
    from src.config import settings
    
    verification_service = get_user_verification_service(settings.bot_username or "bot")
    result = await verification_service.verify_user_exists(str(user_id))
    
    return {
        "success": True,
        "data": {
            "eligible": result['exists'] and result['is_verified'],
            "exists": result['exists'],
            "is_verified": result.get('is_verified', False),
            "binding_url": result.get('binding_url')
        }
    }


@router.get("/premium/packages", tags=["Premium"])
async def get_premium_packages():
    """获取Premium套餐列表"""
    from src.modules.premium.handler import PremiumModule
    
    packages = []
    for months, price in PremiumModule.PACKAGES.items():
        packages.append({
            "months": months,
            "price": price,
            "currency": "USDT",
            "discount": 0 if months == 3 else (10 if months == 6 else 20)
        })
    
    return {
        "success": True,
        "data": packages
    }


# ==================== 订单接口 ====================

@router.post("/orders", tags=["Orders"])
async def create_order(
    request: OrderCreateRequest,
    _: str = Depends(api_key_auth)
):
    """创建订单（需要认证）"""
    try:
        order = await order_manager.create_order(
            request.user_id,
            request.base_amount
        )
        
        if not order:
            raise HTTPException(status_code=400, detail="Failed to create order")
        
        return {
            "success": True,
            "data": {
                "order_id": order.order_id,
                "base_amount": order.base_amount,
                "total_amount": order.total_amount,
                "unique_suffix": order.unique_suffix,
                "status": order.status,
                "expires_at": order.expires_at.isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}", tags=["Orders"])
async def get_order(
    order_id: str,
    _: str = Depends(api_key_auth)
):
    """获取订单详情（需要认证）"""
    order = await order_manager.get_order(order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "success": True,
        "data": {
            "order_id": order.order_id,
            "user_id": order.user_id,
            "base_amount": order.base_amount,
            "total_amount": order.total_amount,
            "status": order.status,
            "created_at": order.created_at.isoformat(),
            "expires_at": order.expires_at.isoformat()
        }
    }


@router.get("/orders/user/{user_id}", tags=["Orders"])
async def get_user_orders(
    user_id: int,
    status: Optional[str] = Query(None, description="订单状态过滤"),
    limit: int = Query(10, le=100),
    _: str = Depends(api_key_auth)
):
    """获取用户订单列表（需要认证）"""
    orders = await order_manager.get_user_orders(user_id, status=status, limit=limit)
    
    return {
        "success": True,
        "data": [
            {
                "order_id": order.order_id,
                "base_amount": order.base_amount,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at.isoformat()
            }
            for order in orders
        ]
    }


# ==================== 钱包接口 ====================

@router.get("/wallet/balance/{user_id}", tags=["Wallet"])
async def get_user_balance(
    user_id: int,
    _: str = Depends(api_key_auth)
):
    """获取用户余额（需要认证）"""
    wallet_manager = WalletManager()
    balance = await wallet_manager.get_balance(user_id)
    
    return UserBalanceResponse(
        user_id=user_id,
        balance=balance,
        currency="USDT",
        updated_at=datetime.now()
    )


@router.post("/wallet/deposit", tags=["Wallet"])
async def add_balance(
    user_id: int,
    amount: float,
    reason: str = "API deposit",
    _: str = Depends(api_key_auth)
):
    """增加用户余额（需要认证）"""
    wallet_manager = WalletManager()
    new_balance = await wallet_manager.add_balance(user_id, amount, reason)
    
    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "amount_added": amount,
            "new_balance": new_balance,
            "reason": reason
        }
    }


# ==================== 消息接口 ====================

@router.post("/message/send", tags=["Message"])
async def send_message(
    request: SendMessageRequest,
    _: str = Depends(api_key_auth)
):
    """发送消息给用户（需要认证）"""
    from telegram import Bot
    from src.config import settings
    
    try:
        bot = Bot(token=settings.bot_token)
        await bot.send_message(
            chat_id=request.user_id,
            text=request.message,
            parse_mode=request.parse_mode,
            disable_notification=request.disable_notification
        )
        
        return {
            "success": True,
            "message": "Message sent successfully"
        }
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/broadcast", tags=["Message"])
async def broadcast_message(
    message: str,
    user_ids: list[int],
    parse_mode: str = "HTML",
    _: str = Depends(api_key_auth)
):
    """广播消息给多个用户（需要认证）"""
    from telegram import Bot
    from src.config import settings
    
    bot = Bot(token=settings.bot_token)
    success_count = 0
    failed_count = 0
    
    for user_id in user_ids:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=parse_mode,
                disable_notification=True
            )
            success_count += 1
        except Exception as e:
            logger.warning(f"Failed to send message to {user_id}: {e}")
            failed_count += 1
    
    return {
        "success": True,
        "data": {
            "total": len(user_ids),
            "success": success_count,
            "failed": failed_count
        }
    }


# ==================== 实时汇率接口 ====================

@router.get("/rates/usdt", tags=["Rates"])
async def get_usdt_rates():
    """获取USDT实时汇率"""
    from src.rates.service import get_or_refresh_rates
    
    rates = await get_or_refresh_rates()
    
    return {
        "success": True,
        "data": rates
    }


# ==================== 能量兑换接口 ====================

@router.get("/energy/packages", tags=["Energy"])
async def get_energy_packages():
    """获取能量套餐列表"""
    # 从 legacy 导入业务逻辑类
    from src.legacy.energy.models import EnergyPackage, EnergyPriceConfig
    
    config = EnergyPriceConfig()
    packages = [
        {"name": "6.5万能量", "amount": 65000, "price_trx": config.small_energy_price},
        {"name": "13.1万能量", "amount": 131000, "price_trx": config.large_energy_price},
    ]
    
    return {
        "success": True,
        "data": packages
    }


@router.post("/energy/calculate", tags=["Energy"])
async def calculate_energy_price(
    energy_amount: int
):
    """计算能量价格"""
    # 从 legacy 导入业务逻辑类
    from src.legacy.energy.models import EnergyPriceConfig
    
    config = EnergyPriceConfig()
    if energy_amount == 65000:
        price = config.small_energy_price
    elif energy_amount == 131000:
        price = config.large_energy_price
    else:
        price = 0
    
    return {
        "success": True,
        "data": {"energy_amount": energy_amount, "price_trx": price}
    }
