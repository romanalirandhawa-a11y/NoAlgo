from __future__ import annotations

import csv
import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar, TextIO

from src.data.models import Candle, Instrument
from src.market.candle_processor import CandleProcessor, CandleValidationError

logger = logging.getLogger(__name__)


class HistoricalDataError(Exception):
    pass


class CandleCSVReader:
    REQUIRED_COLUMNS: ClassVar[set[str]] = {"timestamp", "open", "high", "low", "close"}
    OPTIONAL_COLUMNS: ClassVar[set[str]] = {"volume", "instrument"}

    def __init__(self, instrument: Instrument, timeframe: str = "M1") -> None:
        self.instrument = instrument
        self.timeframe = timeframe

    def load(self, path: str | Path) -> list[Candle]:
        path = Path(path)
        if not path.exists():
            raise HistoricalDataError(f"Historical data file not found: {path}")
        with path.open("r", newline="", encoding="utf-8") as f:
            return self._parse(f)

    def _parse(self, f: TextIO) -> list[Candle]:
        reader = csv.DictReader(f)
        self._validate_header(reader.fieldnames or [])
        raw_rows: list[dict[str, str]] = []
        for row_number, row in enumerate(reader, start=2):
            raw_rows.append(dict(row))

        seen: set[datetime] = set()
        candles: list[Candle] = []
        gaps: list[str] = []
        for row in raw_rows:
            ts = self._parse_timestamp(row.get("timestamp", ""), row_number)
            if ts in seen:
                raise HistoricalDataError(f"Duplicate timestamp at row {row_number}: {ts}")
            seen.add(ts)
            open_ = self._parse_float(row["open"], "open", row_number)
            high = self._parse_float(row["high"], "high", row_number)
            low = self._parse_float(row["low"], "low", row_number)
            close = self._parse_float(row["close"], "close", row_number)
            candle = Candle(
                instrument=self.instrument,
                timestamp=ts,
                timeframe=self.timeframe,
                open=open_,
                high=high,
                low=low,
                close=close,
            )
            try:
                CandleProcessor.validate_candle(candle)
            except CandleValidationError as exc:
                raise HistoricalDataError(f"Invalid candle at row {row_number}: {exc}") from exc
            candles.append(candle)

        candles.sort(key=lambda c: c.timestamp)
        self._detect_gaps(candles, gaps)
        if gaps:
            logger.warning("Historical data gaps detected:\n%s", "\n".join(gaps))
        return candles

    def _validate_header(self, fieldnames: Sequence[str]) -> None:
        missing = sorted(self.REQUIRED_COLUMNS - set(fieldnames))
        if missing:
            raise HistoricalDataError(f"Missing required CSV columns: {', '.join(missing)}")

    def _parse_timestamp(self, value: str, row_number: int) -> datetime:
        value = value.strip()
        if not value:
            raise HistoricalDataError(f"Empty timestamp at row {row_number}")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
            try:
                dt = datetime.strptime(value, fmt)  # noqa: DTZ007
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue
        raise HistoricalDataError(f"Unsupported timestamp format at row {row_number}: {value}")

    def _parse_float(self, value: str, field: str, row_number: int) -> float:
        value = value.strip()
        if not value:
            raise HistoricalDataError(f"Empty {field} at row {row_number}")
        try:
            return float(value)
        except ValueError as exc:
            raise HistoricalDataError(f"Invalid {field} at row {row_number}: {value}") from exc

    def _detect_gaps(self, candles: list[Candle], gaps: list[str]) -> None:
        if len(candles) < 2:
            return
        expected_minutes = 1
        for i in range(1, len(candles)):
            delta = (candles[i].timestamp - candles[i - 1].timestamp).total_seconds() / 60.0
            if delta > expected_minutes + 0.5:
                gaps.append(
                    f"Gap between {candles[i-1].timestamp.isoformat()} and {candles[i].timestamp.isoformat()}: {delta:.1f} minutes"
                )
