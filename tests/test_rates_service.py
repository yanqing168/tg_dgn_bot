import json
from types import SimpleNamespace

import pytest

from src.rates import service as rates_service


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class DummyClient:
    def __init__(self, payloads):
        self._payloads = payloads
        self._index = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        payload = self._payloads[self._index]
        self._index += 1
        return DummyResponse(payload)


@pytest.mark.asyncio
async def test_fetch_usdt_cny_from_okx_parses_response(monkeypatch):
    payloads = [
        {"code": "0", "data": {"items": [{"price": "7.10", "paymentMethods": ["bank"]}]}},
        {"code": "0", "data": {"items": [{"price": "7.11", "paymentMethods": ["aliPay"]}]}},
        {"code": "0", "data": {"items": [{"price": "7.12", "paymentMethods": ["wechat"]}]}},
    ]

    class ClientFactory:
        def __call__(self, *args, **kwargs):
            return DummyClient(payloads.copy())

    monkeypatch.setattr(rates_service.httpx, "AsyncClient", ClientFactory())

    prices = await rates_service.fetch_usdt_cny_from_okx()

    assert prices["bank"]["min_price"] == pytest.approx(7.10)
    assert prices["alipay"]["min_price"] == pytest.approx(7.11)
    assert prices["wechat"]["min_price"] == pytest.approx(7.12)
    assert prices["bank"]["merchants"][0]["name"] == "商家"


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def set(self, key, value, ex=None):
        self.store[key] = SimpleNamespace(value=value, ttl=ex)
        return True


@pytest.mark.asyncio
async def test_refresh_usdt_rates_writes_redis(monkeypatch):
    fake_redis = FakeRedis()

    async def fake_fetch():
        return {
            "bank": {"min_price": 7.1, "merchants": [{"price": 7.1, "name": "A"}]},
            "alipay": {"min_price": 7.12, "merchants": [{"price": 7.12, "name": "B"}]},
            "wechat": {"min_price": 7.15, "merchants": [{"price": 7.15, "name": "C"}]},
        }

    monkeypatch.setattr(rates_service, "fetch_usdt_cny_from_okx", fake_fetch)

    payload = await rates_service.refresh_usdt_rates(fake_redis)

    assert payload["base"] == pytest.approx(7.1)
    assert payload["wechat"] == pytest.approx(7.15)
    assert rates_service.USDT_RATES_REDIS_KEY in fake_redis.store
    stored = fake_redis.store[rates_service.USDT_RATES_REDIS_KEY]
    saved_payload = json.loads(stored.value)
    assert saved_payload["details"]["bank"]["merchants"][0]["name"] == "A"
    assert stored.ttl == rates_service.settings.usdt_rates_cache_ttl
