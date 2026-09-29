
import pytest

from src.data.models import Instrument
from src.market.alpha_vantage_provider import AlphaVantageProvider
from src.market.factory import create_provider
from src.market.mock_provider import MockMarketDataProvider
from src.market.twelve_data_provider import TwelveDataProvider


@pytest.mark.asyncio
async def test_mock_tick() -> None:
    provider = MockMarketDataProvider()
    inst = Instrument(symbol="EUR/USD")
    tick = await provider.get_tick(inst)
    assert tick.instrument == inst
    assert tick.bid < tick.ask
    assert tick.last > 0


@pytest.mark.asyncio
async def test_mock_candles() -> None:
    provider = MockMarketDataProvider()
    inst = Instrument(symbol="EUR/USD")
    candles = await provider.get_candles(inst, "M1", 10)
    assert len(candles) == 10
    assert all(c.timeframe == "M1" for c in candles)
    assert all(c.high >= c.low for c in candles)


@pytest.mark.asyncio
async def test_mock_snapshot() -> None:
    provider = MockMarketDataProvider()
    inst = Instrument(symbol="EUR/USD")
    snapshot = await provider.get_snapshot(inst, "M1", 10)
    assert len(snapshot.candles) == 10
    assert snapshot.current_tick is not None


@pytest.mark.asyncio
async def test_alpha_vantage_request_uses_compact_outputsize() -> None:
    provider = AlphaVantageProvider(api_key="test-key")
    inst = Instrument(symbol="EUR/USD")
    captured: dict[str, object] = {}

    async def fake_request(params: dict[str, str]) -> dict[str, object]:
        captured.update(params)
        return {"Time Series FX (1min)": {}}

    from unittest.mock import patch

    with patch.object(provider, "_request", fake_request):
        await provider.get_candles(inst, "M1", 1)

    assert captured["function"] == "FX_INTRADAY"
    assert captured["from_symbol"] == "EUR"
    assert captured["to_symbol"] == "USD"
    assert captured["interval"] == "1min"
    assert captured["outputsize"] == "compact"
    assert captured["apikey"] == "test-key"


@pytest.mark.asyncio
async def test_alpha_vantage_get_tick_uses_candles_not_snapshot() -> None:
    provider = AlphaVantageProvider(api_key="test-key")
    inst = Instrument(symbol="EUR/USD")
    captured: dict[str, object] = {}

    async def fake_request(params: dict[str, str]) -> dict[str, object]:
        captured.update(params)
        return {
            "Time Series FX (1min)": {
                "2026-09-23 12:34:00": {"1. open": "1.17320", "2. high": "1.17325", "3. low": "1.17310", "4. close": "1.17322"},
            }
        }

    from unittest.mock import patch

    with patch.object(provider, "_request", fake_request):
        tick = await provider.get_tick(inst)

    assert tick.last == 1.17322
    assert captured["function"] == "FX_INTRADAY"
    assert captured["interval"] == "1min"


@pytest.mark.asyncio
async def test_twelve_data_provider_can_be_constructed() -> None:
    provider = TwelveDataProvider(api_key="test-key")
    assert provider is not None


@pytest.mark.asyncio
async def test_twelve_data_request_parameters() -> None:
    provider = TwelveDataProvider(api_key="test-key")
    inst = Instrument(symbol="EUR/USD")
    captured: dict[str, object] = {}

    async def fake_request(params: dict[str, str]) -> dict[str, object]:
        captured.update(params)
        return {"status": "ok", "values": []}

    from unittest.mock import patch

    with patch.object(provider, "_request", fake_request):
        await provider.get_candles(inst, "M1", 5)

    assert captured["symbol"] == "EUR/USD"
    assert captured["interval"] == "1min"
    assert captured["outputsize"] == "5"
    assert captured["timezone"] == "UTC"
    assert captured["apikey"] == "test-key"


@pytest.mark.asyncio
async def test_twelve_data_response_is_mapped_to_candles() -> None:
    provider = TwelveDataProvider(api_key="test-key")
    inst = Instrument(symbol="EUR/USD")
    values = [
        {"datetime": "2026-09-23 12:34:00", "open": "1.17320", "high": "1.17325", "low": "1.17310", "close": "1.17322"},
        {"datetime": "2026-09-23 12:35:00", "open": "1.17322", "high": "1.17327", "low": "1.17315", "close": "1.17324"},
    ]

    async def fake_request(params: dict[str, str]) -> dict[str, object]:
        return {"status": "ok", "values": values}

    from unittest.mock import patch

    with patch.object(provider, "_request", fake_request):
        candles = await provider.get_candles(inst, "M1", 10)

    assert len(candles) == 2
    assert candles[0].timestamp.isoformat() == "2026-09-23T12:34:00+00:00"
    assert candles[1].timestamp.isoformat() == "2026-09-23T12:35:00+00:00"
    assert candles[0].open == 1.17320
    assert candles[0].high == 1.17325
    assert candles[0].low == 1.17310
    assert candles[0].close == 1.17322
    assert candles[0].timeframe == "M1"


@pytest.mark.asyncio
async def test_twelve_data_empty_values_returns_no_candles() -> None:
    provider = TwelveDataProvider(api_key="test-key")
    inst = Instrument(symbol="EUR/USD")

    async def fake_request(params: dict[str, str]) -> dict[str, object]:
        return {"status": "ok", "values": []}

    from unittest.mock import patch

    with patch.object(provider, "_request", fake_request):
        candles = await provider.get_candles(inst, "M1", 10)

    assert candles == []


def test_factory_recognizes_twelve_data() -> None:
    provider = create_provider(name="twelvedata", api_key="", twelvedata_api_key="test-key")
    assert isinstance(provider, TwelveDataProvider)


def test_factory_twelvedata_requires_api_key() -> None:
    with pytest.raises(ValueError) as exc_info:
        create_provider(name="twelvedata", api_key="", twelvedata_api_key="")
    assert "TWELVEDATA_API_KEY" in str(exc_info.value)

