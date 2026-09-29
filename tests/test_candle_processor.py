from datetime import datetime, timedelta, timezone

import pytest

from src.data.models import Candle, Instrument
from src.market.candle_processor import CandleProcessor, CandleValidationError


def _candle(ts: datetime) -> Candle:
    return Candle(
        instrument=Instrument(symbol="EUR/USD"),
        timestamp=ts,
        timeframe="M1",
        open=1.0,
        high=1.0005,
        low=0.9995,
        close=1.0002,
    )


def test_normalize_timestamp_naive() -> None:
    naive = datetime(2024, 1, 1, 12, 0, 0, tzinfo=None)  # noqa: DTZ001
    normalized = CandleProcessor.normalize_timestamp(naive)
    assert normalized.tzinfo is not None


def test_validate_candle_rejects_negative_ohlc() -> None:
    bad = _candle(datetime.now(timezone.utc)).model_copy(update={"open": -1.0})
    with pytest.raises(CandleValidationError):
        CandleProcessor.validate_candle(bad)


def test_validate_candle_rejects_inverted_ohlc() -> None:
    bad = _candle(datetime.now(timezone.utc)).model_copy(update={"high": 0.5, "low": 1.5})
    with pytest.raises(CandleValidationError):
        CandleProcessor.validate_candle(bad)


def test_process_sorts_and_deduplicates() -> None:
    now = datetime.now(timezone.utc)
    ts1 = now.replace(second=0, microsecond=0)
    ts2 = ts1.replace(minute=ts1.minute + 1)
    candles = [_candle(ts2), _candle(ts1), _candle(ts1)]
    result = CandleProcessor.process(candles)
    assert len(result) == 2
    assert result[0].timestamp == ts1


def test_process_removes_stale_candles() -> None:
    now = datetime.now(timezone.utc)
    stale_ts = now - timedelta(hours=2)
    fresh_ts = now.replace(second=0, microsecond=0)
    candles = [_candle(stale_ts), _candle(fresh_ts)]
    result = CandleProcessor.process(candles)
    assert len(result) == 1
    assert result[0].timestamp == fresh_ts
