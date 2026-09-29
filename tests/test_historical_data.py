from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.backtesting.historical_data import CandleCSVReader, HistoricalDataError
from src.data.models import Instrument


def _instrument() -> Instrument:
    return Instrument(symbol="EUR/USD")


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(rows)


def test_load_valid_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_csv(
        csv_path,
        [
            {"timestamp": "2024-01-01 00:00:00", "open": "1.0", "high": "1.001", "low": "0.999", "close": "1.0005", "volume": "100"},
            {"timestamp": "2024-01-01 00:01:00", "open": "1.0005", "high": "1.002", "low": "1.0", "close": "1.001", "volume": "110"},
        ],
    )
    reader = CandleCSVReader(instrument=_instrument(), timeframe="M1")
    candles = reader.load(csv_path)
    assert len(candles) == 2
    assert candles[0].timestamp == datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert candles[1].timestamp == datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc)


def test_load_csv_missing_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        f.write("timestamp,open,high\n")
        f.write("2024-01-01 00:00:00,1.0,1.001\n")
    reader = CandleCSVReader(instrument=_instrument(), timeframe="M1")
    with pytest.raises(HistoricalDataError, match="Missing required CSV columns"):
        reader.load(csv_path)


def test_load_csv_invalid_ohlc(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad_ohlc.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        f.write("timestamp,open,high,low,close\n")
        f.write("2024-01-01 00:00:00,1.0,0.999,1.001,1.0005\n")
    reader = CandleCSVReader(instrument=_instrument(), timeframe="M1")
    with pytest.raises(HistoricalDataError, match="Invalid candle"):
        reader.load(csv_path)


def test_load_csv_duplicate_timestamps(tmp_path: Path) -> None:
    csv_path = tmp_path / "dup.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        f.write("timestamp,open,high,low,close\n")
        f.write("2024-01-01 00:00:00,1.0,1.001,0.999,1.0005\n")
        f.write("2024-01-01 00:00:00,1.0005,1.002,1.0,1.001\n")
    reader = CandleCSVReader(instrument=_instrument(), timeframe="M1")
    with pytest.raises(HistoricalDataError, match="Duplicate timestamp"):
        reader.load(csv_path)


def test_load_csv_gap_detection(tmp_path: Path) -> None:
    csv_path = tmp_path / "gap.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        f.write("timestamp,open,high,low,close\n")
        f.write("2024-01-01 00:00:00,1.0,1.001,0.999,1.0005\n")
        f.write("2024-01-01 00:05:00,1.0005,1.002,1.0,1.001\n")
    reader = CandleCSVReader(instrument=_instrument(), timeframe="M1")
    candles = reader.load(csv_path)
    assert len(candles) == 2


def test_load_csv_malformed_timestamp(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad_ts.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        f.write("timestamp,open,high,low,close\n")
        f.write("not-a-date,1.0,1.001,0.999,1.0005\n")
    reader = CandleCSVReader(instrument=_instrument(), timeframe="M1")
    with pytest.raises(HistoricalDataError, match="Unsupported timestamp format"):
        reader.load(csv_path)


def test_load_csv_file_not_found() -> None:
    reader = CandleCSVReader(instrument=_instrument(), timeframe="M1")
    with pytest.raises(HistoricalDataError, match="not found"):
        reader.load("nonexistent.csv")
