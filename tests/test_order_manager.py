"""Tests for OrderManager user confirmation helpers.

These tests cover the new mark_user_confirmed helper using an in-memory
SQLite database so no Redis dependency is required.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, Order


def _load_order_manager_module():
    """Locate the module exposing OrderManager (order.py in this project)."""

    for module_name in ("src.payments.order_manager", "src.payments.order"):
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        if getattr(module, "OrderManager", None) is not None:
            return module
    pytest.fail("Unable to import OrderManager implementation for tests")


def _require_mark_user_confirmed(manager_cls):
    if not hasattr(manager_cls, "mark_user_confirmed"):
        pytest.fail("OrderManager.mark_user_confirmed is not implemented")


@pytest.fixture()
def db_session():
    """Provide isolated in-memory SQLite session for SQLAlchemy models."""

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def order_manager(db_session, monkeypatch):
    """Instantiate OrderManager bound to the in-memory session."""

    module = _load_order_manager_module()
    manager_cls = module.OrderManager
    _require_mark_user_confirmed(manager_cls)

    # Monkeypatch SessionLocal used by OrderManager (if present) so it relies on
    # our in-memory SQLAlchemy session. OrderManager in this project stores
    # orders in Redis, but mark_user_confirmed touches ORM models, so binding the
    # session keeps the code isolated from external state.
    if hasattr(module, "SessionLocal"):
        monkeypatch.setattr(module, "SessionLocal", lambda: db_session)

    manager = manager_cls()
    # Also stub redis_client so mark_user_confirmed can call self.connect()
    # without attempting a real Redis connection.
    manager.redis_client = None
    return manager


def _create_order_record(session, **overrides):
    data = {
        "order_id": overrides.get("order_id", "TEST_ORDER"),
        "user_id": overrides.get("user_id", 987654321),
        "order_type": overrides.get("order_type", "premium"),
        "base_amount": overrides.get("base_amount", 1_000_000),
        "unique_suffix": overrides.get("unique_suffix", 123),
        "amount_usdt": overrides.get("amount_usdt", 1_000_123),
        "status": overrides.get("status", "PENDING"),
        "recipient": overrides.get("recipient"),
        "premium_months": overrides.get("premium_months"),
        "tx_hash": overrides.get("tx_hash"),
        "user_tx_hash": overrides.get("user_tx_hash"),
        "user_confirmed_at": overrides.get("user_confirmed_at"),
        "user_confirm_source": overrides.get("user_confirm_source"),
        "created_at": overrides.get("created_at", datetime.now()),
        "paid_at": overrides.get("paid_at"),
        "delivered_at": overrides.get("delivered_at"),
        "expires_at": overrides.get(
            "expires_at", datetime.now() + timedelta(hours=1)
        ),
    }

    order = Order(**data)
    session.add(order)
    session.commit()
    return order


@pytest.mark.asyncio
async def test_order_manager_mark_user_confirmed_updates_fields(order_manager, db_session):
    """mark_user_confirmed should persist tx hash, source, and timestamp."""

    target_order = _create_order_record(db_session, order_id="CONFIRM_001")

    updated = await order_manager.mark_user_confirmed(
        target_order.order_id,
        tx_hash="0xabc123",
        source="manual",
    )

    assert updated.user_tx_hash == "0xabc123"
    assert updated.user_confirm_source == "manual"
    assert isinstance(updated.user_confirmed_at, datetime)

    refreshed = db_session.query(Order).filter_by(order_id=target_order.order_id).one()
    assert refreshed.user_tx_hash == "0xabc123"
    assert refreshed.user_confirm_source == "manual"
    assert isinstance(refreshed.user_confirmed_at, datetime)


@pytest.mark.asyncio
async def test_order_manager_mark_user_confirmed_idempotent(order_manager, db_session):
    """Subsequent invocations should overwrite confirmation metadata."""

    target_order = _create_order_record(db_session, order_id="CONFIRM_002")

    await order_manager.mark_user_confirmed(
        target_order.order_id,
        tx_hash="0x111111",
        source="manual",
    )

    await order_manager.mark_user_confirmed(
        target_order.order_id,
        tx_hash="0x222222",
        source="admin",
    )

    refreshed = db_session.query(Order).filter_by(order_id=target_order.order_id).one()
    assert refreshed.user_tx_hash == "0x222222"
    assert refreshed.user_confirm_source == "admin"
    assert isinstance(refreshed.user_confirmed_at, datetime)
