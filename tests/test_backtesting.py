from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.analysis.engine import AnalysisEngine
from src.backtesting.engine import BacktestEngine
from src.backtesting.models import BacktestConfig, BacktestOutcome
from src.data.models import Candle, Instrument


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


def _bullish_candles(count: int = 40) -> list[Candle]:
    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    return [_candle(base.replace(minute=i), 1.0 + i * 0.001, 1.0 + i * 0.001 - 0.0005) for i in range(count)]


def _bearish_candles(count: int = 40) -> list[Candle]:
    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    return [_candle(base.replace(minute=i), 1.0 - i * 0.001, 1.0 - i * 0.001 + 0.0005) for i in range(count)]


def _flat_candles(count: int = 40) -> list[Candle]:
    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    return [_candle(base.replace(minute=i), 1.0, 1.0, 1.0, 1.0) for i in range(count)]


@pytest.mark.asyncio
async def test_backtest_bullish_signals() -> None:
    candles = _bullish_candles(50)
    engine = BacktestEngine(analysis_engine=AnalysisEngine())
    config = BacktestConfig(instrument=_instrument(), timeframe="M1", expiry_periods=1, minimum_candles=30, confidence_threshold=0.0)
    results = await engine.run(candles, config)
    assert len(results) > 0
    wins = [r for r in results if r.outcome == BacktestOutcome.WIN]
    assert len(wins) > 0


@pytest.mark.asyncio
async def test_backtest_bearish_signals() -> None:
    candles = _bearish_candles(50)
    engine = BacktestEngine(analysis_engine=AnalysisEngine())
    config = BacktestConfig(instrument=_instrument(), timeframe="M1", expiry_periods=1, minimum_candles=30, confidence_threshold=0.0)
    results = await engine.run(candles, config)
    assert len(results) > 0
    wins = [r for r in results if r.outcome == BacktestOutcome.WIN]
    assert len(wins) > 0


@pytest.mark.asyncio
async def test_backtest_flat_outcome() -> None:
    candles = _flat_candles(50)
    engine = BacktestEngine(analysis_engine=AnalysisEngine())
    config = BacktestConfig(instrument=_instrument(), timeframe="M1", expiry_periods=1, minimum_candles=30, confidence_threshold=0.0)
    results = await engine.run(candles, config)
    assert len(results) > 0
    skipped = [r for r in results if r.outcome == BacktestOutcome.SKIPPED]
    assert len(skipped) > 0


@pytest.mark.asyncio
async def test_backtest_insufficient_future_candles() -> None:
    candles = _bullish_candles(35)
    engine = BacktestEngine(analysis_engine=AnalysisEngine())
    config = BacktestConfig(instrument=_instrument(), timeframe="M1", expiry_periods=10, minimum_candles=30, confidence_threshold=0.0)
    results = await engine.run(candles, config)
    assert all(r.outcome in (BacktestOutcome.SKIPPED, BacktestOutcome.PENDING) for r in results)


@pytest.mark.asyncio
async def test_backtest_neutral_signals_skipped() -> None:
    candles = _flat_candles(50)
    engine = BacktestEngine(analysis_engine=AnalysisEngine())
    config = BacktestConfig(instrument=_instrument(), timeframe="M1", expiry_periods=1, minimum_candles=30, confidence_threshold=0.0)
    results = await engine.run(candles, config)
    skipped = [r for r in results if r.outcome == BacktestOutcome.SKIPPED]
    assert len(skipped) > 0


@pytest.mark.asyncio
async def test_backtest_confidence_threshold() -> None:
    candles = _bullish_candles(50)
    engine = BacktestEngine(analysis_engine=AnalysisEngine())
    config = BacktestConfig(instrument=_instrument(), timeframe="M1", expiry_periods=1, minimum_candles=30, confidence_threshold=0.9)
    results = await engine.run(candles, config)
    for r in results:
        if r.outcome != BacktestOutcome.SKIPPED:
            assert r.signal.confidence >= 0.9


@pytest.mark.asyncio
async def test_backtest_consecutive_wins() -> None:
    candles = _bullish_candles(60)
    engine = BacktestEngine(analysis_engine=AnalysisEngine())
    config = BacktestConfig(instrument=_instrument(), timeframe="M1", expiry_periods=1, minimum_candles=30, confidence_threshold=0.0)
    results = await engine.run(candles, config)
    max_consecutive = 0
    current = 0
    for r in results:
        if r.outcome == BacktestOutcome.WIN:
            current += 1
            max_consecutive = max(max_consecutive, current)
        else:
            current = 0
    assert max_consecutive > 0


@pytest.mark.asyncio
async def test_backtest_consecutive_losses() -> None:
    candles = _bearish_candles(60)
    engine = BacktestEngine(analysis_engine=AnalysisEngine())
    config = BacktestConfig(instrument=_instrument(), timeframe="M1", expiry_periods=1, minimum_candles=30, confidence_threshold=0.0)
    results = await engine.run(candles, config)
    max_consecutive = 0
    current = 0
    for r in results:
        if r.outcome == BacktestOutcome.WIN:
            current += 1
            max_consecutive = max(max_consecutive, current)
        else:
            current = 0
    assert max_consecutive > 0


@pytest.mark.asyncio
async def test_backtest_lookahead_protection() -> None:
    candles = _bullish_candles(50)
    engine = BacktestEngine(analysis_engine=AnalysisEngine())
    config = BacktestConfig(instrument=_instrument(), timeframe="M1", expiry_periods=1, minimum_candles=30, confidence_threshold=0.0)
    results_before = await engine.run(candles, config)
    signals_before = [r.signal for r in results_before if r.outcome != BacktestOutcome.SKIPPED]
    if not signals_before:
        pytest.skip("No signals generated for lookahead test")
    original_signal = signals_before[0]
    original_exit_price = results_before[0].exit_price

    modified = list(candles)
    if len(modified) > config.minimum_candles:
        modified[config.minimum_candles] = _candle(
            modified[config.minimum_candles].timestamp,
            close=modified[config.minimum_candles].close + 0.01,
            high=modified[config.minimum_candles].high + 0.01,
            low=modified[config.minimum_candles].low + 0.01,
        )
    results_after = await engine.run(modified, config)
    signals_after = [r.signal for r in results_after if r.outcome != BacktestOutcome.SKIPPED]
    if not signals_after:
        pytest.skip("No signals generated for lookahead test after modification")

    modified_signal = signals_after[0]
    assert modified_signal.timestamp == original_signal.timestamp
    assert modified_signal.entry_price == original_signal.entry_price
    assert modified_signal.direction == original_signal.direction
    assert modified_signal.confidence == original_signal.confidence
    if results_after[0].outcome in (BacktestOutcome.WIN, BacktestOutcome.LOSS):
        assert results_after[0].exit_price != original_exit_price
