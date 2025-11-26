"""Job queue tasks for USDT rate refreshing."""
from __future__ import annotations

import logging
from telegram.ext import ContextTypes

from .service import refresh_usdt_rates

logger = logging.getLogger(__name__)


async def refresh_usdt_rates_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic task that refreshes USDT-CNY rates."""
    del context  # Unused but kept for PTB job signature compatibility
    try:
        await refresh_usdt_rates()
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.warning("USDT 汇率刷新任务失败: %s", exc)
