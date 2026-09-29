from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.data.models import Candle
from src.utils.time import utc_now

logger = logging.getLogger(__name__)


class CandleValidationError(Exception):
    pass


class CandleProcessor:
    @staticmethod
    def normalize_timestamp(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def validate_candle(cls, candle: Candle) -> Candle:
        if candle.open <= 0 or candle.high <= 0 or candle.low <= 0 or candle.close <= 0:
            raise CandleValidationError("Invalid OHLC values")
        if candle.high < max(candle.open, candle.close):
            raise CandleValidationError("High is lower than open/close")
        if candle.low > min(candle.open, candle.close):
            raise CandleValidationError("Low is higher than open/close")
        if candle.high < candle.low:
            raise CandleValidationError("High is lower than low")
        return candle

    @staticmethod
    def sort_candles(candles: list[Candle]) -> list[Candle]:
        return sorted(candles, key=lambda c: c.timestamp)

    @staticmethod
    def remove_duplicates(candles: list[Candle]) -> list[Candle]:
        seen: set[datetime] = set()
        result: list[Candle] = []
        for candle in candles:
            if candle.timestamp not in seen:
                seen.add(candle.timestamp)
                result.append(candle)
        return result

    @staticmethod
    def is_stale(candle: Candle, now: datetime | None = None) -> bool:
        now = now or utc_now()
        return (now - candle.timestamp).total_seconds() > 3600

    @classmethod
    def process(cls, candles: list[Candle], now: datetime | None = None) -> list[Candle]:
        processed: list[Candle] = []
        seen: set[datetime] = set()
        for raw in candles:
            try:
                raw.timestamp = cls.normalize_timestamp(raw.timestamp)
                cls.validate_candle(raw)
                if raw.timestamp in seen:
                    continue
                seen.add(raw.timestamp)
                if cls.is_stale(raw, now):
                    continue
                processed.append(raw)
            except CandleValidationError:
                raise
            except Exception as exc:
                raise CandleValidationError(f"Unexpected candle error: {exc}") from exc
        return cls.sort_candles(processed)
