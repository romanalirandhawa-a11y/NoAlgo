from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.data.models import Instrument
from src.market.alpha_vantage_provider import AlphaVantageProvider, MarketDataError
from src.market.factory import create_provider
from src.market.live_service import LiveMarketDataService


def test_create_provider_mock() -> None:
    provider = create_provider("mock")
    assert provider is not None


def test_create_provider_alpha_vantage_requires_key() -> None:
    with pytest.raises(ValueError):
        create_provider("alpha_vantage")


def test_create_provider_alpha_vantage_with_key() -> None:
    provider = create_provider("alpha_vantage", api_key="DEMO")
    assert isinstance(provider, AlphaVantageProvider)


def test_create_provider_unknown() -> None:
    with pytest.raises(ValueError):
        create_provider("unknown")


@pytest.mark.asyncio
async def test_live_service_retry_on_failure() -> None:
    provider = AsyncMock()
    provider.get_candles = AsyncMock(side_effect=MarketDataError("fail"))
    service = LiveMarketDataService(provider=provider, max_retries=2, base_delay=0.01)
    with pytest.raises(MarketDataError):
        await service.get_candles(Instrument(symbol="EUR/USD"), "M1", 10)
    assert provider.get_candles.call_count == 2


@pytest.mark.asyncio
async def test_live_service_success_updates_state() -> None:
    from src.data.models import Candle

    provider = AsyncMock()
    provider.get_candles = AsyncMock(
        return_value=[
            Candle(
                instrument=Instrument(symbol="EUR/USD"),
                timestamp=datetime.now(timezone.utc),
                timeframe="M1",
                open=1.0,
                high=1.001,
                low=0.999,
                close=1.0005,
            )
        ]
    )
    service = LiveMarketDataService(provider=provider)
    result = await service.get_candles(Instrument(symbol="EUR/USD"), "M1", 10)
    assert len(result) == 1
    assert service.last_error is None
