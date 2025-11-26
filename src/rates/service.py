"""USDT 汇率刷新与缓存服务。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import redis.asyncio as redis

from ..config import settings

logger = logging.getLogger(__name__)

USDT_RATES_REDIS_KEY = "usdt_cny_rates"
OKX_C2C_URL = "https://www.okx.com/v3/c2c/tradingOrders/books"
OKX_C2C_COMMON_PARAMS = {
    "quoteCurrency": "cny",
    "baseCurrency": "usdt",
    "side": "sell",
}
PAYMENT_METHODS = {
    "bank": "bank",
    "alipay": "alipay",
    "wechat": "wechat",
}

_redis_client: Optional[redis.Redis] = None


async def _get_redis_client() -> Optional[redis.Redis]:
    """惰性创建 Redis 客户端。"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password or None,
                decode_responses=True,
            )
        except Exception as exc:  # pragma: no cover - 极端配置错误
            logger.warning("初始化 Redis 客户端失败: %s", exc)
            return None
    return _redis_client


async def fetch_usdt_cny_from_okx() -> Dict[str, Dict[str, Any]]:
    """从 OKX C2C 获取不同支付渠道的 USDT-CNY 报价与商家列表。"""
    channel_prices: Dict[str, Dict[str, Any]] = {
        key: {"min_price": None, "merchants": []} for key in PAYMENT_METHODS
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        for channel, payment_method in PAYMENT_METHODS.items():
            params = {**OKX_C2C_COMMON_PARAMS, "paymentMethod": payment_method}
            try:
                response = await client.get(OKX_C2C_URL, params=params)
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:  # pragma: no cover - 网络异常
                logger.warning("OKX C2C 请求失败 (%s): %s", channel, exc)
                continue

            code = str(payload.get("code", ""))
            if code != "0":
                msg = payload.get("msg", "OKX response error")
                logger.warning("OKX C2C 返回错误 (%s): %s %s", channel, code, msg)
                continue

            data = payload.get("data") or {}
            items = None
            if isinstance(data, dict):
                items = data.get("sell") or data.get("items") or data.get("buy")

            if not isinstance(items, list) or not items:
                logger.warning("OKX C2C 数据为空 (%s): %s", channel, json.dumps(payload)[:200])
                continue

            merchants: List[Dict[str, Any]] = []
            for entry in items[:10]:
                if not isinstance(entry, dict):
                    continue
                price_str = entry.get("price")
                try:
                    price_val = round(float(price_str), 4)
                except (TypeError, ValueError):
                    logger.warning("OKX C2C 价格解析失败 (%s): %s", channel, price_str)
                    continue

                name = entry.get("nickName") or entry.get("merchantId") or entry.get("publicUserId") or "商家"
                merchants.append({
                    "price": price_val,
                    "name": name,
                })

            if merchants:
                channel_prices[channel]["min_price"] = merchants[0]["price"]
                channel_prices[channel]["merchants"] = merchants

    if not any(info.get("min_price") is not None for info in channel_prices.values()):
        raise ValueError("OKX C2C 返回为空或不可用")

    return channel_prices


def build_rates_payload(channel_prices: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """根据渠道报价构建缓存载荷。"""
    updated_at = datetime.now(timezone.utc).isoformat()

    def _first_available_price() -> float:
        for key in ("bank", "alipay", "wechat"):
            price = channel_prices.get(key, {}).get("min_price")
            if price is not None:
                return float(price)
        return 0.0

    base_price = _first_available_price()

    payload: Dict[str, Any] = {
        "updated_at": updated_at,
        "base": round(base_price, 4) if base_price else 0.0,
    }

    details: Dict[str, Any] = {}
    for key in ("bank", "alipay", "wechat"):
        channel_info = channel_prices.get(key, {})
        price = channel_info.get("min_price")
        payload[key] = round(price, 4) if price is not None else None
        details[key] = {
            "merchants": channel_info.get("merchants", []),
        }

    payload["details"] = details

    return payload


async def refresh_usdt_rates(redis_client: Optional[redis.Redis] = None) -> Optional[Dict[str, Any]]:
    """刷新 USDT 汇率并写入 Redis。"""
    try:
        channel_prices = await fetch_usdt_cny_from_okx()
    except Exception as exc:
        logger.warning("获取 OKX 汇率失败: %s", exc)
        return None

    payload = build_rates_payload(channel_prices)

    if redis_client is None:
        redis_client = await _get_redis_client()

    if redis_client is None:
        logger.warning("Redis 未配置或不可用，跳过缓存写入")
        return payload

    try:
        await redis_client.set(
            USDT_RATES_REDIS_KEY,
            json.dumps(payload),
            ex=settings.usdt_rates_cache_ttl,
        )
        logger.info("USDT 汇率已刷新：%s", payload)
    except Exception as exc:
        logger.warning("写入 Redis 失败: %s", exc)

    return payload


async def get_cached_rates(redis_client: Optional[redis.Redis] = None) -> Optional[Dict[str, Any]]:
    """读取 Redis 中缓存的汇率。"""
    if redis_client is None:
        redis_client = await _get_redis_client()

    if redis_client is None:
        return None

    try:
        raw = await redis_client.get(USDT_RATES_REDIS_KEY)
    except Exception as exc:
        logger.warning("读取 Redis 失败: %s", exc)
        return None

    if not raw:
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Redis 中的 USDT 汇率数据格式错误，忽略。")
        return None


async def get_or_refresh_rates(
    redis_client: Optional[redis.Redis] = None,
    *,
    force_refresh: bool = False,
) -> Optional[Dict[str, Any]]:
    """优先读取缓存，必要时刷新。"""
    if not force_refresh:
        cached = await get_cached_rates(redis_client)
        if cached:
            return cached

    return await refresh_usdt_rates(redis_client)
