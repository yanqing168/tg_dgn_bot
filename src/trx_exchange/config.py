"""Configuration helpers for the TRX Exchange module."""
from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel

from ..config import settings


class TRXExchangeConfig(BaseModel):
    """Typed configuration snapshot for TRX exchange dependencies."""

    receive_address: str = ""
    send_address: str = ""
    private_key: str = ""
    qrcode_file_id: str = ""
    default_rate: Decimal = Decimal("0")
    test_mode: bool = True

    @classmethod
    def from_settings(cls) -> "TRXExchangeConfig":
        """Create config instance from global settings."""
        return cls(
            receive_address=settings.trx_exchange_receive_address or "",
            send_address=settings.trx_exchange_send_address or "",
            private_key=settings.trx_exchange_private_key or "",
            qrcode_file_id=settings.trx_exchange_qrcode_file_id or "",
            default_rate=Decimal(str(settings.trx_exchange_default_rate)),
            test_mode=bool(settings.trx_exchange_test_mode),
        )
