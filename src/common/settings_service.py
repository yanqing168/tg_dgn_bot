"""Centralized access to mutable runtime settings."""

from __future__ import annotations

import logging
from typing import Optional

from src.bot_admin.config_manager import config_manager


logger = logging.getLogger(__name__)


DEFAULT_ORDER_TIMEOUT = 15  # minutes
DEFAULT_ADDRESS_COOLDOWN = 2  # minutes

ORDER_TIMEOUT_KEY = "order_timeout_minutes"
ADDRESS_COOLDOWN_KEY = "address_query_rate_limit"


def _parse_int(value: Optional[str], *, default: int, min_value: int = 1) -> int:
    """Safely parse positive integers with fallback."""

    if value is None:
        return default
    try:
        parsed = int(str(value).strip())
        if parsed < min_value:
            return default
        return parsed
    except (TypeError, ValueError):
        logger.warning("Invalid setting value '%s', fallback to default %s", value, default)
        return default


def get_order_timeout_minutes() -> int:
    """Return the configured order timeout in minutes with safe default."""

    raw_value = config_manager.get_setting(ORDER_TIMEOUT_KEY, str(DEFAULT_ORDER_TIMEOUT))
    return _parse_int(raw_value, default=DEFAULT_ORDER_TIMEOUT, min_value=1)


def set_order_timeout_minutes(minutes: int, updated_by: Optional[int] = None) -> bool:
    """Persist the new order timeout (minutes) into the settings store."""

    if minutes < 1:
        raise ValueError("Order timeout must be positive")

    return config_manager.set_setting(
        ORDER_TIMEOUT_KEY,
        str(minutes),
        updated_by or 0,
        "订单超时时间（分钟）",
    )


def get_address_cooldown_minutes() -> int:
    """Return cooldown between address queries (minutes) with default fallback."""

    raw_value = config_manager.get_setting(ADDRESS_COOLDOWN_KEY, str(DEFAULT_ADDRESS_COOLDOWN))
    return _parse_int(raw_value, default=DEFAULT_ADDRESS_COOLDOWN, min_value=1)


def set_address_cooldown_minutes(minutes: int, updated_by: Optional[int] = None) -> bool:
    """Persist cooldown between address queries (minutes)."""

    if minutes < 1:
        raise ValueError("Address cooldown must be positive")

    return config_manager.set_setting(
        ADDRESS_COOLDOWN_KEY,
        str(minutes),
        updated_by or 0,
        "地址查询限频（分钟）",
    )
