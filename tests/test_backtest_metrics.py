from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.backtesting.metrics import compute_metrics
from src.backtesting.models import BacktestOutcome, BacktestResult, BacktestSignal
from src.data.models import Instrument


def _instrument() -> Instrument:
    return Instrument(symbol="EUR/USD")


def _signal(ts: datetime, confidence: float, direction: str = "BULLISH") -> BacktestSignal:
    return BacktestSignal(
        timestamp=ts,
        instrument=_instrument(),
        timeframe="M1",
        entry_price=1.0,
        direction=direction,
        confidence=confidence,
    )


def _result(outcome: BacktestOutcome, signal: BacktestSignal, price_change: float = 0.0) -> BacktestResult:
    return BacktestResult(
        signal=signal,
        outcome=outcome,
        exit_price=signal.entry_price + price_change,
        price_change=price_change,
    )


def test_compute_metrics_basic() -> None:
    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    signals = [_signal(base.replace(minute=i), 0.5 + i * 0.1) for i in range(5)]
    results = [
        _result(BacktestOutcome.WIN, signals[0], 0.001),
        _result(BacktestOutcome.LOSS, signals[1], -0.001),
        _result(BacktestOutcome.WIN, signals[2], 0.002),
        _result(BacktestOutcome.SKIPPED, signals[3]),
        _result(BacktestOutcome.PENDING, signals[4]),
    ]
    metrics = compute_metrics(results)
    assert metrics.total_opportunities == 5
    assert metrics.total_signals == 3
    assert metrics.total_skipped == 1
    assert metrics.total_wins == 2
    assert metrics.total_losses == 1
    assert metrics.total_pending == 1
    assert metrics.win_rate == pytest.approx(2 / 3)


def test_compute_metrics_empty() -> None:
    metrics = compute_metrics([])
    assert metrics.total_opportunities == 0
    assert metrics.win_rate is None
    assert metrics.average_confidence is None


def test_compute_metrics_all_skipped() -> None:
    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    signals = [_signal(base, 0.1)]
    results = [_result(BacktestOutcome.SKIPPED, signals[0])]
    metrics = compute_metrics(results)
    assert metrics.total_skipped == 1
    assert metrics.win_rate is None


def test_compute_metrics_consecutive() -> None:
    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    signals = [_signal(base.replace(minute=i), 0.8) for i in range(6)]
    results = [
        _result(BacktestOutcome.WIN, signals[0], 0.001),
        _result(BacktestOutcome.WIN, signals[1], 0.001),
        _result(BacktestOutcome.WIN, signals[2], 0.001),
        _result(BacktestOutcome.LOSS, signals[3], -0.001),
        _result(BacktestOutcome.LOSS, signals[4], -0.001),
        _result(BacktestOutcome.WIN, signals[5], 0.001),
    ]
    metrics = compute_metrics(results)
    assert metrics.max_consecutive_wins == 3
    assert metrics.max_consecutive_losses == 2


def test_compute_metrics_confidence_buckets() -> None:
    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    results = [
        _result(BacktestOutcome.WIN, _signal(base, 0.55), 0.001),
        _result(BacktestOutcome.LOSS, _signal(base.replace(minute=1), 0.65), -0.001),
        _result(BacktestOutcome.WIN, _signal(base.replace(minute=2), 0.75), 0.001),
        _result(BacktestOutcome.WIN, _signal(base.replace(minute=3), 0.85), 0.001),
        _result(BacktestOutcome.LOSS, _signal(base.replace(minute=4), 0.95), -0.001),
    ]
    metrics = compute_metrics(results)
    assert "50-59" in metrics.confidence_buckets
    assert "60-69" in metrics.confidence_buckets
    assert "70-79" in metrics.confidence_buckets
    assert "80-89" in metrics.confidence_buckets
    assert "90-100" in metrics.confidence_buckets
