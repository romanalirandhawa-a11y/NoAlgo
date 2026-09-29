from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TypeVar

from src.data.models import Candle, Instrument, MarketSnapshot, MarketTick
from src.market.alpha_vantage_provider import MarketDataError
from src.market.candle_processor import CandleProcessor, CandleValidationError
from src.market.provider import MarketDataProvider
from src.utils.time import utc_now

logger = logging.getLogger(__name__)

T = TypeVar("T")


class LiveMarketDataService:
    def __init__(
        self,
        provider: MarketDataProvider,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> None:
        self.provider = provider
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.last_success: datetime | None = None
        self.last_error: str | None = None
        self.consecutive_failures: int = 0

    async def get_tick(self, instrument: Instrument) -> MarketTick:
        return await self._with_retry(self.provider.get_tick, instrument)

    async def get_candles(
        self,
        instrument: Instrument,
        timeframe: str,
        count: int,
        end_time: datetime | None = None,
    ) -> list[Candle]:
        candles = await self._with_retry(self.provider.get_candles, instrument, timeframe, count, end_time)
        try:
            processed = CandleProcessor.process(candles, utc_now())
        except CandleValidationError as exc:
            self.last_error = f"Validation error: {exc}"
            self.consecutive_failures += 1
            logger.error("Candle validation failed: %s", exc)
            return []
        self.last_success = utc_now()
        self.last_error = None
        self.consecutive_failures = 0
        return processed

    async def get_snapshot(
        self,
        instrument: Instrument,
        timeframe: str,
        count: int,
    ) -> MarketSnapshot:
        candles = await self.get_candles(instrument, timeframe, count)
        tick: MarketTick | None = None
        if candles:
            try:
                tick = await self.get_tick(instrument)
            except MarketDataError as exc:
                logger.debug("Tick fetch failed: %s", exc)
        return MarketSnapshot(
            instrument=instrument,
            timestamp=utc_now(),
            candles=candles,
            current_tick=tick,
        )

    async def _with_retry(self, func: Callable[..., Awaitable[T]], *args: object) -> T:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                return await func(*args)
            except MarketDataError as exc:
                last_exc = exc
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning("Retrying after error: %s (attempt %s)", exc, attempt + 1)
                    await asyncio.sleep(delay)
                else:
                    self.consecutive_failures += 1
                    self.last_error = str(exc)
                    logger.error("Operation failed after retries: %s", exc)
                    raise
        raise last_exc  # type: ignore[misc]


