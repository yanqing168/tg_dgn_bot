import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest

from src.menu.main_menu import MainMenuHandler


class DummyMessage:
    def __init__(self):
        self.text = None

    async def reply_text(self, text, reply_markup=None, parse_mode=None):
        self.text = text
        self.reply_markup = reply_markup


class DummyCallbackQuery:
    def __init__(self):
        self.answered = False
        self.text = None

    async def answer(self):
        self.answered = True

    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
        self.text = text
        self.reply_markup = reply_markup


@pytest.mark.asyncio
async def test_show_usdt_rates_all_channel(monkeypatch):
    fake_rates = {
        "updated_at": datetime(2025, 1, 1, 12, 0, 0).isoformat(),
        "base": 7.1,
        "bank": 7.1,
        "alipay": 7.12,
        "wechat": 7.13,
        "details": {
            "bank": {"merchants": [{"price": 7.1, "name": "顺宝"}]},
            "alipay": {"merchants": [{"price": 7.12, "name": "灵感商贸"}]},
            "wechat": {"merchants": [{"price": 7.13, "name": "千百惠"}]},
        },
    }

    async def fake_get_rates():
        return fake_rates

    monkeypatch.setattr("src.menu.main_menu.get_or_refresh_rates", fake_get_rates)

    message = DummyMessage()
    update = SimpleNamespace(message=message, callback_query=None)
    context = SimpleNamespace()

    await MainMenuHandler.show_usdt_rates_all(update, context)

    assert "✅ 全部渠道报价" in message.text
    assert "顺宝" in message.text
    assert "🏦" in message.text and "💴" in message.text and "🟢" in message.text


@pytest.mark.asyncio
async def test_show_usdt_rates_channel_switch(monkeypatch):
    fake_rates = {
        "updated_at": datetime(2025, 1, 2, 8, 0, 0).isoformat(),
        "base": 7.2,
        "bank": 7.2,
        "alipay": 7.21,
        "wechat": 7.22,
        "details": {
            "bank": {"merchants": [{"price": 7.2, "name": "顺宝"}]},
            "alipay": {"merchants": [{"price": 7.21, "name": "灵感商贸"}]},
            "wechat": {"merchants": [{"price": 7.22, "name": "千百惠"}]},
        },
    }

    async def fake_get_rates():
        return fake_rates

    monkeypatch.setattr("src.menu.main_menu.get_or_refresh_rates", fake_get_rates)

    query = DummyCallbackQuery()
    update = SimpleNamespace(message=None, callback_query=query)
    context = SimpleNamespace()

    await MainMenuHandler.show_usdt_rates_bank(update, context)

    assert query.answered is True
    assert "银行卡渠道" in query.text
    assert "顺宝" in query.text
    assert "支付宝渠道" not in query.text

    await MainMenuHandler.show_usdt_rates_wechat(update, context)
    assert "微信渠道" in query.text
    assert "千百惠" in query.text
