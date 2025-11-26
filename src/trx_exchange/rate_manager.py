"""TRX Exchange Rate Manager - Fixed Rate with Admin Control."""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, String, DECIMAL, DateTime
from sqlalchemy.orm import Session

from .config import TRXExchangeConfig
from ..database import Base

logger = logging.getLogger(__name__)


class TRXExchangeRate(Base):
    """TRX Exchange Rate Configuration."""

    __tablename__ = "trx_exchange_rates"

    id = Column(String(10), primary_key=True, default="current", comment="Rate ID (always 'current')")
    rate = Column(DECIMAL(10, 6), nullable=False, comment="TRX/USDT Rate (1 USDT = X TRX)")
    updated_at = Column(DateTime, nullable=False, comment="Last Update Time")
    updated_by = Column(String(50), nullable=False, comment="Updated by (admin_user_id or 'system')")

    def __repr__(self):
        return f"<TRXExchangeRate(rate={self.rate}, updated_at={self.updated_at})>"


class RateManager:
    """Manage TRX Exchange Rate with Cache."""

    # In-memory cache
    _cached_rate: Optional[Decimal] = None
    _cache_expires_at: Optional[datetime] = None
    _cache_ttl_seconds = 3600  # 1 hour
    _config: TRXExchangeConfig = TRXExchangeConfig.from_settings()

    @classmethod
    def configure(cls, config: TRXExchangeConfig) -> None:
        """Override default configuration (used by handler factory)."""
        cls._config = config

    @classmethod
    def get_rate(cls, db: Session) -> Decimal:
        """
        Get current TRX/USDT exchange rate.

        Returns locked rate from database with 1-hour cache.
        Falls back to config default if no rate in database.

        Args:
            db: SQLAlchemy session

        Returns:
            TRX/USDT rate (e.g., Decimal('3.05') means 1 USDT = 3.05 TRX)
        """
        now = datetime.now(timezone.utc)

        # Return cached rate if valid
        if cls._cached_rate and cls._cache_expires_at and now < cls._cache_expires_at:
            logger.debug(f"Using cached TRX rate: {cls._cached_rate}")
            return cls._cached_rate

        # Fetch from database
        rate_config = db.query(TRXExchangeRate).filter_by(id="current").first()

        if rate_config:
            rate = rate_config.rate
            logger.info(f"Loaded TRX rate from DB: {rate} (updated: {rate_config.updated_at})")
        else:
            # Fallback to config default
            rate = Decimal(str(cls._config.default_rate))
            logger.warning(f"No rate in DB, using default: {rate}")

        # Update cache
        cls._cached_rate = rate
        cls._cache_expires_at = now + timedelta(seconds=cls._cache_ttl_seconds)

        return rate

    @classmethod
    def set_rate(cls, db: Session, new_rate: Decimal, admin_user_id: int) -> None:
        """
        Set new TRX/USDT exchange rate (Admin only).

        Args:
            db: SQLAlchemy session
            new_rate: New rate (e.g., Decimal('3.05'))
            admin_user_id: Telegram user ID of admin

        Raises:
            ValueError: If rate is invalid (≤ 0)
        """
        if new_rate <= 0:
            raise ValueError(f"Invalid rate: {new_rate} (must be > 0)")

        now = datetime.now(timezone.utc)

        # Update or insert rate
        rate_config = db.query(TRXExchangeRate).filter_by(id="current").first()

        if rate_config:
            rate_config.rate = new_rate
            rate_config.updated_at = now
            rate_config.updated_by = str(admin_user_id)
            logger.info(f"Updated TRX rate: {new_rate} (by user {admin_user_id})")
        else:
            rate_config = TRXExchangeRate(
                id="current",
                rate=new_rate,
                updated_at=now,
                updated_by=str(admin_user_id),
            )
            db.add(rate_config)
            logger.info(f"Created TRX rate: {new_rate} (by user {admin_user_id})")

        db.commit()

        # Clear cache to force reload
        cls._clear_cache()

    @classmethod
    def _clear_cache(cls) -> None:
        """Clear cached rate (used after admin update)."""
        cls._cached_rate = None
        cls._cache_expires_at = None
        logger.debug("Cleared TRX rate cache")

    @classmethod
    def calculate_trx_amount(cls, usdt_amount: Decimal, rate: Decimal) -> Decimal:
        """
        Calculate TRX amount from USDT amount.

        Args:
            usdt_amount: USDT amount (e.g., Decimal('10.000'))
            rate: TRX/USDT rate (e.g., Decimal('3.05'))

        Returns:
            TRX amount with 6 decimal places (e.g., Decimal('30.500000'))
        """
        trx_amount = usdt_amount * rate
        return trx_amount.quantize(Decimal("0.000001"))
