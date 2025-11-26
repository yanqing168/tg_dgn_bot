"""TRX Sender - Handle TRX Transfers (Test Mode)."""

import logging
from decimal import Decimal
from typing import Optional

from .config import TRXExchangeConfig
from ..config import settings  # Needed for tests that patch module-level settings

logger = logging.getLogger(__name__)


class TRXSender:
    """
    TRX Transfer Handler (Test Mode).

    In production, configure real private key and enable transfer.
    """

    def __init__(self, config: Optional[TRXExchangeConfig] = None):
        """Initialize TRX sender."""
        if config is not None:
            self.config = config
        else:
            # Build config snapshot using module-level settings (patchable in tests)
            def _as_str(attr: str, default: str = "") -> str:
                value = getattr(settings, attr, default)
                return str(value) if value is not None else default

            def _as_decimal(attr: str, default: Decimal = Decimal("0")) -> Decimal:
                value = getattr(settings, attr, default)
                try:
                    return Decimal(str(value))
                except Exception:
                    return default

            self.config = TRXExchangeConfig(
                receive_address=_as_str("trx_exchange_receive_address"),
                send_address=_as_str("trx_exchange_send_address"),
                private_key=_as_str("trx_exchange_private_key"),
                qrcode_file_id=_as_str("trx_exchange_qrcode_file_id"),
                default_rate=_as_decimal("trx_exchange_default_rate"),
                test_mode=bool(getattr(settings, "trx_exchange_test_mode", True)),
            )
        self.test_mode = self.config.test_mode
        self.sender_address = self.config.send_address
        self.private_key = self.config.private_key

        if self.test_mode:
            logger.info("TRXSender initialized in TEST MODE (no real transfers)")
        else:
            logger.info(f"TRXSender initialized (sender: {self.sender_address})")

    def send_trx(
        self,
        recipient_address: str,
        amount: Decimal,
        order_id: str,
    ) -> Optional[str]:
        """
        Send TRX to recipient address.

        Args:
            recipient_address: User's TRX receiving address
            amount: TRX amount to send (e.g., Decimal('30.500000'))
            order_id: Order ID for logging

        Returns:
            Transaction hash if successful, None if failed

        Raises:
            Exception: If transfer fails (network error, insufficient balance, etc.)
        """
        if self.test_mode:
            logger.info(
                f"[TEST MODE] TRX Transfer: {amount} TRX → {recipient_address} (order: {order_id})"
            )
            # Return mock transaction hash
            return f"mock_tx_hash_{order_id}"

        # Production mode: real TRX transfer
        logger.info(f"Sending {amount} TRX to {recipient_address} (order: {order_id})")

        try:
            # TODO: Implement real TRX transfer using tronpy
            # Example:
            # from tronpy import Tron
            # from tronpy.keys import PrivateKey
            #
            # client = Tron(network='mainnet')
            # priv_key = PrivateKey(bytes.fromhex(self.private_key))
            # txn = (
            #     client.trx.transfer(self.sender_address, recipient_address, int(amount * 1_000_000))
            #     .build()
            #     .sign(priv_key)
            # )
            # result = txn.broadcast()
            # return result['txid']

            raise NotImplementedError(
                "Production TRX transfer not implemented. "
                "Please configure real private key and implement tronpy transfer logic."
            )

        except Exception as e:
            logger.error(f"TRX transfer failed (order: {order_id}): {e}", exc_info=True)
            raise

    def validate_address(self, address: str) -> bool:
        """
        Validate TRX address format.

        Args:
            address: TRX address to validate

        Returns:
            True if valid, False otherwise
        """
        # Basic validation: T prefix + 34 characters
        if not address or len(address) != 34 or not address.startswith("T"):
            return False

        # Check Base58 character set (includes 0 and O)
        import re
        base58_pattern = r'^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+$'
        if not re.match(base58_pattern, address):
            return False

        return True


# Test code for manual verification
if __name__ == "__main__":
    """
    Test TRX Transfer Logic.

    Usage:
        python -m src.trx_exchange.trx_sender
    """
    logging.basicConfig(level=logging.INFO)

    sender = TRXSender()

    # Test address validation
    test_addresses = [
        "TFYCFmuhzrKSL1cDkHmWk7HUh31BBBBBB",  # Valid format
        "TRX123",  # Invalid length
        "0x1234567890123456789012345678901234567890",  # Ethereum address
    ]

    print("\n=== Address Validation Test ===")
    for addr in test_addresses:
        is_valid = sender.validate_address(addr)
        print(f"{addr}: {'✅ Valid' if is_valid else '❌ Invalid'}")

    # Test transfer (test mode)
    print("\n=== Transfer Test (Test Mode) ===")
    try:
        tx_hash = sender.send_trx(
            recipient_address="TFYCFmuhzrKSL1cDkHmWk7HUh31BBBBBB",
            amount=Decimal("30.500000"),
            order_id="TEST_ORDER_001",
        )
        print(f"✅ Transfer successful: {tx_hash}")
    except Exception as e:
        print(f"❌ Transfer failed: {e}")

    print("\n=== Production Setup Instructions ===")
    print("1. Install tronpy: pip install tronpy")
    print("2. Set environment variables:")
    print("   - TRX_EXCHANGE_SEND_ADDRESS: Your TRX wallet address")
    print("   - TRX_EXCHANGE_PRIVATE_KEY: Your wallet private key (KEEP SECRET!)")
    print("   - TRX_EXCHANGE_TEST_MODE: false")
    print("3. Implement real transfer logic in send_trx() method")
    print("4. Test with small amount first!")
