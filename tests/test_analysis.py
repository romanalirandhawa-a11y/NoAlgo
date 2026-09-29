from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.analysis.engine import AnalysisEngine
from src.analysis.enums import DataQuality, Momentum, PriceAction, Trend, Volatility
from src.analysis.features import assess_data_quality, compute_confidence, compute_overall_bias
from src.analysis.indicators import (
    atr,
    classify_momentum,
    classify_price_action,
    classify_rsi,
    classify_trend,
    classify_volatility,
    ema,
    rsi,
)
from src.analysis.indicators import (
    momentum as momentum_indicator,
)
from src.data.models import Candle, Instrument, MarketSnapshot


def _instrument() -> Instrument:
    return Instrument(symbol="EUR/USD")


def _candle(ts: datetime, close: float, open_: float | None = None, high: float | None = None, low: float | None = None) -> Candle:
    open_ = open_ if open_ is not None else close
    high = high if high is not None else max(open_, close)
    low = low if low is not None else min(open_, close)
    return Candle(
        instrument=_instrument(),
        timestamp=ts,
        timeframe="M1",
        open=open_,
        high=high,
        low=low,
        close=close,
    )


def _snapshot(candles: list[Candle]) -> MarketSnapshot:
    ts = candles[-1].timestamp if candles else datetime.now(timezone.utc)
    return MarketSnapshot(
        instrument=_instrument(),
        timestamp=ts,
        candles=candles,
    )


def test_ema_calculation() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = ema(values, 3)
    assert result[2] is not None
    assert result[0] is None
    assert result[1] is None


def test_rsi_calculation() -> None:
    closes = [44.0, 44.5, 43.5, 44.0, 44.5, 45.0, 45.5, 46.0, 45.5, 45.0, 44.5, 45.0, 45.5, 46.0, 46.5]
    result = rsi(closes, 14)
    assert result[14] is not None
    assert 0 <= result[14] <= 100


def test_atr_calculation() -> None:
    highs = [1.0, 1.01, 1.02, 1.01, 1.02, 1.03, 1.04, 1.03, 1.04, 1.05, 1.06, 1.05, 1.06, 1.07, 1.08]
    lows = [0.99, 1.0, 1.01, 1.0, 1.01, 1.02, 1.03, 1.02, 1.03, 1.04, 1.05, 1.04, 1.05, 1.06, 1.07]
    closes = [1.0, 1.005, 1.015, 1.005, 1.015, 1.025, 1.035, 1.025, 1.035, 1.045, 1.055, 1.045, 1.055, 1.065, 1.075]
    result = atr(highs, lows, closes, 5)
    assert result[5] is not None
    assert result[5] > 0


def test_momentum_calculation() -> None:
    closes = [1.0, 1.1, 1.2, 1.3, 1.4]
    result = momentum_indicator(closes, 2)
    assert result[2] == pytest.approx(0.2)
    assert result[3] == pytest.approx(0.2)
    assert result[4] == pytest.approx(0.2)


def test_classify_trend() -> None:
    assert classify_trend(10.0, 9.0, 8.0) == Trend.BULLISH
    assert classify_trend(8.0, 9.0, 10.0) == Trend.BEARISH
    assert classify_trend(9.0, 9.0, 9.0) == Trend.NEUTRAL
    assert classify_trend(9.0, None, 8.0) == Trend.NEUTRAL


def test_classify_momentum() -> None:
    assert classify_momentum(0.5) == Momentum.POSITIVE
    assert classify_momentum(-0.5) == Momentum.NEGATIVE
    assert classify_momentum(0.0) == Momentum.NEUTRAL


def test_classify_volatility() -> None:
    assert classify_volatility(0.01, 1.0) == Volatility.HIGH
    assert classify_volatility(0.0001, 1.0) == Volatility.LOW
    assert classify_volatility(0.0005, 1.0) == Volatility.NORMAL


def test_classify_rsi() -> None:
    assert classify_rsi(60.0) == Trend.BULLISH
    assert classify_rsi(40.0) == Trend.BEARISH
    assert classify_rsi(50.0) == Trend.NEUTRAL
    assert classify_rsi(None) == Trend.NEUTRAL


def test_classify_price_action_bullish() -> None:
    candles = [_candle(datetime(2024, 1, 1, 0, i, tzinfo=timezone.utc), 1.0 + i * 0.001, 1.0 + i * 0.001 - 0.0005) for i in range(5)]
    assert classify_price_action(candles) == PriceAction.BULLISH


def test_classify_price_action_bearish() -> None:
    candles = [_candle(datetime(2024, 1, 1, 0, i, tzinfo=timezone.utc), 1.0 - i * 0.001, 1.0 - i * 0.001 + 0.0005) for i in range(5)]
    assert classify_price_action(candles) == PriceAction.BEARISH


def test_classify_price_action_insufficient() -> None:
    assert classify_price_action([]) == PriceAction.NEUTRAL


def test_assess_data_quality() -> None:
    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    def dummy(n: int) -> Candle:
        return _candle(base.replace(minute=n), 1.0)
    assert assess_data_quality([dummy(i) for i in range(20)]) == DataQuality.INSUFFICIENT
    assert assess_data_quality([dummy(i) for i in range(30)]) == DataQuality.LIMITED
    assert assess_data_quality([dummy(i) for i in range(40)]) == DataQuality.GOOD


def test_compute_overall_bias() -> None:
    features = {"trend": "BULLISH", "momentum": "POSITIVE", "rsi_trend": "BULLISH", "price_action": "BULLISH"}
    assert compute_overall_bias(features) == "BULLISH"
    features = {"trend": "BEARISH", "momentum": "NEGATIVE", "rsi_trend": "BEARISH", "price_action": "BEARISH"}
    assert compute_overall_bias(features) == "BEARISH"
    features = {"trend": "NEUTRAL", "momentum": "NEUTRAL", "rsi_trend": "NEUTRAL", "price_action": "NEUTRAL"}
    assert compute_overall_bias(features) == "NEUTRAL"


def test_compute_confidence() -> None:
    features = {"trend": "BULLISH", "momentum": "POSITIVE", "rsi_trend": "BULLISH", "price_action": "BULLISH"}
    assert compute_confidence(features) == 1.0
    features = {"trend": "BULLISH", "momentum": "NEGATIVE", "rsi_trend": "BULLISH", "price_action": "BEARISH"}
    assert compute_confidence(features) == 0.0
    features = {"trend": "NEUTRAL", "momentum": "NEUTRAL", "rsi_trend": "NEUTRAL", "price_action": "NEUTRAL"}
    assert compute_confidence(features) == 0.0


@pytest.mark.asyncio
async def test_analysis_engine_insufficient_data() -> None:
    engine = AnalysisEngine()
    result = await engine.analyze(_snapshot([]))
    assert result.data_quality == "INSUFFICIENT"
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_analysis_engine_bullish_sequence() -> None:
    candles = [_candle(datetime(2024, 1, 1, 0, i, tzinfo=timezone.utc), 1.0 + i * 0.001, 1.0 + i * 0.001 - 0.0005) for i in range(40)]
    engine = AnalysisEngine()
    result = await engine.analyze(_snapshot(candles))
    assert result.data_quality == DataQuality.GOOD
    assert result.trend == Trend.BULLISH
    assert result.overall_bias == "BULLISH"
    assert result.confidence > 0.0


@pytest.mark.asyncio
async def test_analysis_engine_bearish_sequence() -> None:
    candles = [_candle(datetime(2024, 1, 1, 0, i, tzinfo=timezone.utc), 1.0 - i * 0.001, 1.0 - i * 0.001 + 0.0005) for i in range(40)]
    engine = AnalysisEngine()
    result = await engine.analyze(_snapshot(candles))
    assert result.data_quality == DataQuality.GOOD
    assert result.trend == Trend.BEARISH
    assert result.overall_bias == "BEARISH"
    assert result.confidence > 0.0


@pytest.mark.asyncio
async def test_analysis_engine_flat_price() -> None:
    candles = [_candle(datetime(2024, 1, 1, 0, i, tzinfo=timezone.utc), 1.0, 1.0, 1.0, 1.0) for i in range(40)]
    engine = AnalysisEngine()
    result = await engine.analyze(_snapshot(candles))
    assert result.data_quality == DataQuality.GOOD
    assert result.overall_bias == "NEUTRAL"


@pytest.mark.asyncio
async def test_analysis_engine_lookahead_protection() -> None:
    engine = AnalysisEngine()
    candles = [_candle(datetime(2024, 1, 1, 0, i, tzinfo=timezone.utc), 1.0 + i * 0.001, 1.0 + i * 0.001 - 0.0005) for i in range(40)]
    result = await engine.analyze(_snapshot(candles))
    assert result.timestamp <= candles[-1].timestamp
    assert result.rsi is not None or result.data_quality in (DataQuality.LIMITED, DataQuality.INSUFFICIENT)
