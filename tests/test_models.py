from __future__ import annotations

from datetime import datetime, timezone

from src.data.models import (
    AnalysisResult,
    Candle,
    Instrument,
    MarketTick,
    PaperTrade,
    TradeResult,
)


def test_instrument_str() -> None:
    inst = Instrument(symbol="EUR/USD")
    assert str(inst) == "EUR/USD"


def test_market_tick_creation() -> None:
    inst = Instrument(symbol="EUR/USD")
    tick = MarketTick(
        instrument=inst,
        timestamp=datetime.now(timezone.utc),
        bid=1.17310,
        ask=1.17330,
        last=1.17320,
    )
    assert tick.bid == 1.17310
    assert tick.ask == 1.17330


def test_candle_creation() -> None:
    inst = Instrument(symbol="EUR/USD")
    candle = Candle(
        instrument=inst,
        timestamp=datetime.now(timezone.utc),
        timeframe="M1",
        open=1.17300,
        high=1.17350,
        low=1.17280,
        close=1.17320,
    )
    assert candle.high == 1.17350
    assert candle.low == 1.17280


def test_analysis_result_defaults() -> None:
    inst = Instrument(symbol="EUR/USD")
    result = AnalysisResult(
        instrument=inst,
        timestamp=datetime.now(timezone.utc),
        direction="NEUTRAL",
        confidence=0.5,
        reason="test",
    )
    assert result.features == {}
    assert result.data_quality == "unknown"


def test_paper_trade_result() -> None:
    inst = Instrument(symbol="EUR/USD")
    trade = PaperTrade(
        id="1",
        instrument=inst,
        timestamp=datetime.now(timezone.utc),
        direction="BULLISH",
        entry_price=1.17300,
        expiry_seconds=60,
    )
    assert trade.result == TradeResult.PENDING
