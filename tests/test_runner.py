from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.backtesting.models import BacktestConfig
from src.backtesting.runner import BacktestRunner
from src.data.models import Candle, Instrument


def _instrument() -> Instrument:
    return Instrument(symbol="EUR/USD")


def _candle(ts: datetime, close: float) -> Candle:
    return Candle(
        instrument=_instrument(),
        timestamp=ts,
        timeframe="M1",
        open=close - 0.0005,
        high=close + 0.0005,
        low=close - 0.0005,
        close=close,
    )


def _candles(count: int = 40) -> list[Candle]:
    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    return [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(count)]


@pytest.mark.asyncio
async def test_runner_executes_backtest(tmp_path: Path) -> None:
    runner = BacktestRunner(output_dir=tmp_path)
    candles = _candles(50)
    config = BacktestConfig(instrument=_instrument(), timeframe="M1", expiry_periods=1, minimum_candles=30, confidence_threshold=0.0)
    metrics, report = await runner.run(candles, config)
    assert metrics.total_opportunities > 0
    assert "BACKTEST REPORT" in report


@pytest.mark.asyncio
async def test_runner_saves_results(tmp_path: Path) -> None:
    runner = BacktestRunner(output_dir=tmp_path)
    candles = _candles(50)
    config = BacktestConfig(instrument=_instrument(), timeframe="M1", expiry_periods=1, minimum_candles=30, confidence_threshold=0.0)
    await runner.run(candles, config)
    files = list(tmp_path.glob("backtest_EUR_USD_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["instrument"] == "EUR/USD"
    assert "metrics" in data
    assert "report" in data


@pytest.mark.asyncio
async def test_runner_date_range_filter(tmp_path: Path) -> None:
    runner = BacktestRunner(output_dir=tmp_path)
    candles = _candles(50)
    start = datetime(2024, 1, 1, 0, 10, tzinfo=timezone.utc)
    end = datetime(2024, 1, 1, 0, 20, tzinfo=timezone.utc)
    config = BacktestConfig(instrument=_instrument(), timeframe="M1", expiry_periods=1, minimum_candles=5, confidence_threshold=0.0, start_time=start, end_time=end)
    metrics, _ = await runner.run(candles, config)
    assert metrics.dataset_start == start
    assert metrics.dataset_end == end
