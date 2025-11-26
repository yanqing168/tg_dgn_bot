from datetime import datetime, timedelta

import pytest

from src.database import Order
from src.orders.query_handler import _build_order_detail_text


def _make_order(**overrides) -> Order:
    now = datetime(2025, 1, 1, 0, 0)
    data = {
        "order_id": overrides.get("order_id", "ORDER-001"),
        "user_id": overrides.get("user_id", 9527),
        "order_type": overrides.get("order_type", "premium"),
        "base_amount": overrides.get("base_amount", 10_000_000),
        "unique_suffix": overrides.get("unique_suffix", 123),
        "amount_usdt": overrides.get("amount_usdt", 10_123_000),
        "status": overrides.get("status", "PENDING"),
        "recipient": overrides.get("recipient", "@demo"),
        "premium_months": overrides.get("premium_months", 3),
        "tx_hash": overrides.get("tx_hash"),
        "user_tx_hash": overrides.get("user_tx_hash"),
        "user_confirmed_at": overrides.get("user_confirmed_at"),
        "user_confirm_source": overrides.get("user_confirm_source"),
        "created_at": overrides.get("created_at", now),
        "paid_at": overrides.get("paid_at"),
        "delivered_at": overrides.get("delivered_at"),
        "expires_at": overrides.get("expires_at", now + timedelta(days=1)),
    }
    return Order(**data)


def test_orders_query_handler_detail_includes_confirmation():
    order = _make_order(
        user_confirmed_at=datetime(2025, 1, 1, 12, 34),
        user_confirm_source="manual",
        user_tx_hash="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
    )

    detail_text = _build_order_detail_text(order)

    assert "👤 用户确认" in detail_text
    assert "manual" in detail_text
    assert "🧾 用户填写 TX Hash" in detail_text
    assert "0xabcd...7890" in detail_text  # masked hash format


def test_orders_query_handler_detail_without_confirmation():
    order = _make_order(
        user_confirmed_at=None,
        user_confirm_source=None,
        user_tx_hash=None,
    )

    detail_text = _build_order_detail_text(order)

    assert "👤 用户确认" not in detail_text
    assert "🧾 用户填写 TX Hash" not in detail_text
