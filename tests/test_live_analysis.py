from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.analysis.engine import AnalysisEngine
from src.analysis.live_analysis import LiveAnalysisResult, LiveAnalysisService
from src.data.models import Candle, Instrument, MarketSnapshot
from src.market.live_service import LiveMarketDataService
from src.market.mock_provider import MockMarketDataProvider


def _instrument() -> Instrument:
    return Instrument(symbol="EUR/USD")


def _candle(ts: datetime) -> Candle:
    return Candle(
        instrument=_instrument(),
        timestamp=ts,
        timeframe="M1",
        open=1.0,
        high=1.0005,
        low=0.9995,
        close=1.0002,
    )


def _snapshot() -> list[Candle]:
    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    return [_candle(base.replace(minute=i)) for i in range(40)]


@pytest.mark.asyncio
async def test_live_analysis_returns_result() -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    service = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    result = await service.analyze(_instrument(), "M1", 30)
    assert isinstance(result, LiveAnalysisResult)
    assert result.instrument == _instrument()
    assert result.timeframe == "M1"
    assert result.latest_price > 0


@pytest.mark.asyncio
async def test_live_analysis_preserves_candles() -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    service = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    result = await service.analyze(_instrument(), "M1", 30)
    assert len(result.candles) > 0


@pytest.mark.asyncio
async def test_live_analysis_result_fields() -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    service = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    result = await service.analyze(_instrument(), "M1", 30)
    assert result.analysis.instrument == _instrument()
    assert result.analysis.direction in ("BULLISH", "BEARISH", "NEUTRAL")
    assert 0.0 <= result.analysis.confidence <= 1.0


@pytest.mark.asyncio
async def test_live_analysis_insufficient_data() -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    service = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    snapshot = MarketSnapshot(
        instrument=_instrument(),
        timestamp=datetime.now(timezone.utc),
        candles=[],
        current_tick=None,
    )
    with patch.object(market_service, "get_snapshot", AsyncMock(return_value=snapshot)):
        result = await service.analyze(_instrument(), "M1", 30)
    assert result.analysis.data_quality == "INSUFFICIENT"
    assert result.analysis.confidence == 0.0


@pytest.mark.asyncio
async def test_live_analysis_provider_error() -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    service = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    with patch.object(market_service, "get_snapshot", AsyncMock(side_effect=RuntimeError("provider failed"))), pytest.raises(RuntimeError):
        await service.analyze(_instrument(), "M1", 30)
