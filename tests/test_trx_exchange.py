"""TRX Exchange Tests."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from types import SimpleNamespace

from telegram.ext import ConversationHandler

from src.trx_exchange.handler import TRXExchangeHandler
from src.trx_exchange.rate_manager import RateManager, TRXExchangeRate
from src.trx_exchange.trx_sender import TRXSender
from src.trx_exchange.models import TRXExchangeOrder


class TestRateManager:
    """Test TRX Exchange Rate Manager."""

    def test_calculate_trx_amount(self):
        """Test TRX amount calculation."""
        usdt = Decimal("10.000")
        rate = Decimal("3.05")
        trx = RateManager.calculate_trx_amount(usdt, rate)
        assert trx == Decimal("30.500000")

    def test_calculate_trx_amount_precision(self):
        """Test TRX amount calculation with precision."""
        usdt = Decimal("7.500")
        rate = Decimal("3.123456")
        trx = RateManager.calculate_trx_amount(usdt, rate)
        assert trx == Decimal("23.425920")

    def test_get_rate_default(self, test_db):
        """Test get rate with default config value."""
        # No rate in DB, should return config default
        rate = RateManager.get_rate(test_db)
        assert rate == Decimal("3.05")  # From settings default

    def test_get_rate_from_db(self, test_db):
        """Test get rate from database."""
        # Create rate in DB
        rate_config = TRXExchangeRate(
            id="current",
            rate=Decimal("3.50"),
            updated_at=datetime.now(timezone.utc),
            updated_by="test_admin",
        )
        test_db.add(rate_config)
        test_db.commit()

        # Clear cache first
        RateManager._clear_cache()

        # Get rate
        rate = RateManager.get_rate(test_db)
        assert rate == Decimal("3.50")

    def test_get_rate_cached(self, test_db):
        """Test rate caching."""
        # Set rate
        RateManager.set_rate(test_db, Decimal("3.60"), 123456)

        # Get rate twice (second should be cached)
        rate1 = RateManager.get_rate(test_db)
        rate2 = RateManager.get_rate(test_db)

        assert rate1 == rate2 == Decimal("3.60")
        assert RateManager._cached_rate == Decimal("3.60")

    def test_set_rate_create(self, test_db):
        """Test set rate (create new)."""
        RateManager.set_rate(test_db, Decimal("4.00"), 123456)

        # Verify in DB
        rate_config = test_db.query(TRXExchangeRate).filter_by(id="current").first()
        assert rate_config is not None
        assert rate_config.rate == Decimal("4.00")
        assert rate_config.updated_by == "123456"

    def test_set_rate_update(self, test_db):
        """Test set rate (update existing)."""
        # Create initial rate
        RateManager.set_rate(test_db, Decimal("3.50"), 111111)

        # Update rate
        RateManager.set_rate(test_db, Decimal("3.80"), 222222)

        # Verify in DB
        rate_config = test_db.query(TRXExchangeRate).filter_by(id="current").first()
        assert rate_config.rate == Decimal("3.80")
        assert rate_config.updated_by == "222222"

    def test_set_rate_invalid(self, test_db):
        """Test set rate with invalid value."""
        with pytest.raises(ValueError, match="Invalid rate"):
            RateManager.set_rate(test_db, Decimal("0"), 123456)

        with pytest.raises(ValueError, match="Invalid rate"):
            RateManager.set_rate(test_db, Decimal("-1.5"), 123456)

    def test_set_rate_clears_cache(self, test_db):
        """Test that set_rate clears cache."""
        # Set initial rate
        RateManager.set_rate(test_db, Decimal("3.50"), 111111)
        RateManager.get_rate(test_db)  # Cache it

        # Update rate
        RateManager.set_rate(test_db, Decimal("4.00"), 222222)

        # Cache should be cleared
        assert RateManager._cached_rate is None


class TestTRXSender:
    """Test TRX Sender."""

    def test_validate_address_valid(self):
        """Test valid TRX address."""
        sender = TRXSender()
        # Valid Base58 address (no 0, O, I, l) - 34 chars total
        assert sender.validate_address("TFYCFmuhzrKSL1cDkHmWk7HUh31ccccccc") is True

    def test_validate_address_invalid_length(self):
        """Test invalid address (wrong length)."""
        sender = TRXSender()
        assert sender.validate_address("TRX123") is False
        assert sender.validate_address("T" + "A" * 40) is False

    def test_validate_address_invalid_prefix(self):
        """Test invalid address (wrong prefix)."""
        sender = TRXSender()
        assert sender.validate_address("AFYCFmuhzrKSL1cDkHmWk7HUh31BBBBBB") is False

    def test_validate_address_empty(self):
        """Test empty address."""
        sender = TRXSender()
        assert sender.validate_address("") is False
        assert sender.validate_address(None) is False

    def test_send_trx_test_mode(self):
        """Test TRX transfer in test mode."""
        sender = TRXSender()
        assert sender.test_mode is True

        tx_hash = sender.send_trx(
            recipient_address="TFYCFmuhzrKSL1cDkHmWk7HUh31BBBBBB",
            amount=Decimal("30.500000"),
            order_id="TEST_ORDER_001",
        )

        assert tx_hash is not None
        assert tx_hash.startswith("mock_tx_hash_")

    def test_send_trx_production_not_implemented(self):
        """Test TRX transfer in production mode (not implemented)."""
        # 需要在 patch 后重新导入并实例化才能生效
        with patch("src.trx_exchange.trx_sender.settings") as mock_settings:
            mock_settings.trx_exchange_test_mode = False
            mock_settings.trx_exchange_send_address = "TSENDER_ADDRESS_123456789012345678"
            mock_settings.trx_exchange_private_key = None
            
            # 在 patch 作用域内创建实例
            sender = TRXSender()
            assert sender.test_mode is False

            with pytest.raises(NotImplementedError, match="Production TRX transfer not implemented"):
                sender.send_trx(
                    recipient_address="TFYCFmuhzrKSL1cDkHmWk7HUh31BBBBBB",
                    amount=Decimal("30.500000"),
                    order_id="TEST_ORDER_001",
                )


class TestTRXExchangeHandler:
    """Test TRX Exchange Handler."""

    def test_generate_order_id(self):
        """Test order ID generation."""
        handler = TRXExchangeHandler()
        order_id = handler.generate_order_id()

        assert order_id.startswith("TRX")
        assert len(order_id) == 19  # TRX + 16 hex chars

    def test_generate_unique_amount(self):
        """Test unique amount generation."""
        handler = TRXExchangeHandler()
        base_amount = Decimal("10")

        unique_amount = handler.generate_unique_amount(base_amount)

        assert unique_amount >= Decimal("10.001")
        assert unique_amount <= Decimal("10.999")
        assert len(str(unique_amount).split(".")[1]) == 3  # 3 decimal places

    def test_generate_unique_amount_different(self):
        """Test that unique amounts are different."""
        handler = TRXExchangeHandler()
        base_amount = Decimal("20")

        amounts = [handler.generate_unique_amount(base_amount) for _ in range(10)]

        # At least some should be different
        assert len(set(amounts)) > 1

    @pytest.mark.asyncio
    async def test_start_exchange(self):
        """Test start exchange flow."""
        handler = TRXExchangeHandler()

        # Mock update
        update = Mock()
        update.message = Mock()
        update.message.reply_text = AsyncMock()

        context = Mock()

        # Start exchange
        result = await handler.start_exchange(update, context)

        # Verify
        assert result == 0  # INPUT_AMOUNT state
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert "TRX 闪兑" in call_args[0][0]
        assert "5 USDT" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_input_amount_valid(self):
        """Test valid amount input."""
        handler = TRXExchangeHandler()

        # Mock update
        update = Mock()
        update.message = Mock()
        update.message.text = "10"
        update.message.reply_text = AsyncMock()

        context = Mock()
        context.user_data = {}

        # Create test DB
        from src.database import SessionLocal

        # 清除 RateManager 缓存，确保 mock 生效
        RateManager._cached_rate = None
        RateManager._cache_expires_at = None
        
        with patch("src.trx_exchange.handler.SessionLocal", return_value=Mock()):
            with patch.object(RateManager, "get_rate", return_value=Decimal("3.05")):
                # Input amount
                result = await handler.input_amount(update, context)

                # Verify
                assert result == 1  # INPUT_ADDRESS state
                assert context.user_data["exchange_usdt_amount"] == Decimal("10")
                assert context.user_data["exchange_rate"] == Decimal("3.05")
                assert context.user_data["exchange_trx_amount"] == Decimal("30.500000")

    @pytest.mark.asyncio
    async def test_input_amount_invalid_format(self):
        """Test invalid amount format."""
        handler = TRXExchangeHandler()

        # Mock update
        update = Mock()
        update.message = Mock()
        update.message.text = "abc"
        update.message.reply_text = AsyncMock()

        context = Mock()

        # Input amount
        result = await handler.input_amount(update, context)

        # Verify
        assert result == 0  # Stay in INPUT_AMOUNT state
        update.message.reply_text.assert_called_once()
        assert "格式错误" in update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_input_amount_too_small(self):
        """Test amount below minimum."""
        handler = TRXExchangeHandler()

        # Mock update
        update = Mock()
        update.message = Mock()
        update.message.text = "3"
        update.message.reply_text = AsyncMock()

        context = Mock()

        # Input amount
        result = await handler.input_amount(update, context)

        # Verify
        assert result == 0  # Stay in INPUT_AMOUNT state
        assert "最低兑换金额为 5 USDT" in update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_input_amount_too_large(self):
        """Test amount above maximum."""
        handler = TRXExchangeHandler()

        # Mock update
        update = Mock()
        update.message = Mock()
        update.message.text = "25000"
        update.message.reply_text = AsyncMock()

        context = Mock()

        # Input amount
        result = await handler.input_amount(update, context)

        # Verify
        assert result == 0  # Stay in INPUT_AMOUNT state
        assert "最高兑换金额为 20,000 USDT" in update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_show_payment_sets_expires_at(self, monkeypatch):
        """Ensure show_payment persists expires_at using configured timeout."""
        handler = TRXExchangeHandler()

        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 123456
        message = Mock()
        message.reply_text = AsyncMock()
        message.reply_photo = AsyncMock()
        update.effective_message = message

        context = SimpleNamespace(
            user_data={
                "exchange_usdt_amount": Decimal("10"),
                "exchange_rate": Decimal("3.05"),
                "exchange_trx_amount": Decimal("30.500000"),
                "exchange_recipient_address": "TTestAddress",
            }
        )

        class FakeSession:
            def __init__(self):
                self.added = None

            def add(self, obj):
                self.added = obj

            def commit(self):
                pass

            def close(self):
                pass

        fake_session = FakeSession()
        monkeypatch.setattr("src.trx_exchange.handler.SessionLocal", lambda: fake_session)
        monkeypatch.setattr("src.trx_exchange.handler.get_order_timeout_minutes", lambda: 45)
        from src.trx_exchange import handler as handler_module

        monkeypatch.setattr(handler_module.settings, "trx_exchange_receive_address", "TRECV")
        monkeypatch.setattr(handler_module.settings, "trx_exchange_qrcode_file_id", "")

        state = await handler.show_payment(update, context)

        assert state == 3  # CONFIRM_PAYMENT
        assert fake_session.added is not None
        delta = fake_session.added.expires_at - fake_session.added.created_at
        assert delta == timedelta(minutes=45)

    @pytest.mark.asyncio
    async def test_input_address_valid(self, monkeypatch):
        """Test valid address input."""
        handler = TRXExchangeHandler()

        # Mock update
        update = Mock()
        update.message = Mock()
        update.message.text = "TFYCFmuhzrKSL1cDkHmWk7HUh31ccccccc"
        update.message.reply_text = AsyncMock()
        update.effective_message = update.message
        update.effective_message.reply_photo = AsyncMock()
        update.effective_message.reply_text = AsyncMock()
        update.effective_user = Mock()
        update.effective_user.id = 123456

        context = Mock()
        context.user_data = {
            "exchange_usdt_amount": Decimal("10"),
            "exchange_rate": Decimal("3.05"),
            "exchange_trx_amount": Decimal("30.500000"),
            "exchange_recipient_address": "TTestAddress",
        }

        class FakeSession:
            def __init__(self):
                self.added = None

            def add(self, obj):
                self.added = obj

            def commit(self):
                pass

            def close(self):
                pass

        fake_session = FakeSession()
        monkeypatch.setattr("src.trx_exchange.handler.SessionLocal", lambda: fake_session)
        monkeypatch.setattr("src.trx_exchange.handler.get_order_timeout_minutes", lambda: 30)
        from src.trx_exchange import handler as handler_module

        monkeypatch.setattr(handler_module.settings, "trx_exchange_receive_address", "TRECV")
        monkeypatch.setattr(handler_module.settings, "trx_exchange_qrcode_file_id", "")

        state = await handler.show_payment(update, context)

        assert state == 3  # CONFIRM_PAYMENT
        assert fake_session.added is not None
        delta = fake_session.added.expires_at - fake_session.added.created_at
        assert delta == timedelta(minutes=30)

    @pytest.mark.asyncio
    async def test_confirm_payment_rejects_expired_order(self, monkeypatch):
        handler = TRXExchangeHandler()

        test_user_id = 12345
        expired_order = SimpleNamespace(
            status="PENDING",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            user_id=test_user_id,  # H2 安全加固需要此字段
        )

        class DummySession:
            def __init__(self, order):
                self.order = order
                self.committed = False
                self.closed = False

            def query(self, *_args, **_kwargs):
                return self

            def filter_by(self, **_kwargs):
                return self

            def first(self):
                return self.order

            def commit(self):
                self.committed = True

            def close(self):
                self.closed = True

        dummy_session = DummySession(expired_order)
        monkeypatch.setattr("src.trx_exchange.handler.SessionLocal", lambda: dummy_session)

        query = Mock()
        query.data = "trx_paid_TRX123"
        query.edit_message_text = AsyncMock()
        query.answer = AsyncMock()

        update = Mock()
        update.callback_query = query
        update.effective_user = Mock()
        update.effective_user.id = test_user_id  # 匹配订单 user_id

        context = Mock()
        context.user_data = {"exchange_order_id": "TRX123"}

        result = await handler.confirm_payment(update, context)

        assert result == ConversationHandler.END
        assert expired_order.status == "EXPIRED"
        assert dummy_session.committed is True
        query.edit_message_text.assert_awaited_with("❌ 订单已过期，请重新发起兑换。")
        assert context.user_data == {}

    @pytest.mark.asyncio
    async def test_handle_payment_callback_skips_expired(self, monkeypatch):
        handler = TRXExchangeHandler()

        expired_order = SimpleNamespace(
            status="PENDING",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )

        class DummySession:
            def __init__(self, order):
                self.order = order
                self.committed = False
                self.closed = False

            def query(self, *_args, **_kwargs):
                return self

            def filter_by(self, **_kwargs):
                return self

            def first(self):
                return self.order

            def commit(self):
                self.committed = True

            def close(self):
                self.closed = True

        dummy_session = DummySession(expired_order)
        monkeypatch.setattr("src.trx_exchange.handler.SessionLocal", lambda: dummy_session)
        handler.trx_sender = Mock()

        await handler.handle_payment_callback("TRX999")

        assert expired_order.status == "EXPIRED"
        assert dummy_session.committed is True
        handler.trx_sender.send_trx.assert_not_called()

    @pytest.mark.asyncio
    async def test_input_address_invalid(self):
        """Test invalid address input."""
        handler = TRXExchangeHandler()

        # Mock update
        update = Mock()
        update.message = Mock()
        update.message.text = "INVALID_ADDRESS"
        update.message.reply_text = AsyncMock()

        context = Mock()

        # Input address
        result = await handler.input_address(update, context)

        # Verify
        assert result == 1  # Stay in INPUT_ADDRESS state
        assert "地址格式错误" in update.message.reply_text.call_args[0][0]
