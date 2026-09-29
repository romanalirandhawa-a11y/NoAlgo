from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.data.models import Candle, Instrument, MarketSnapshot, MarketTick


class MarketDataProvider(ABC):
    @abstractmethod
    async def get_tick(self, instrument: Instrument) -> MarketTick:
        raise NotImplementedError

    @abstractmethod
    async def get_candles(
        self,
        instrument: Instrument,
        timeframe: str,
        count: int,
        end_time: datetime | None = None,
    ) -> list[Candle]:
        raise NotImplementedError

    @abstractmethod
    async def get_snapshot(
        self,
        instrument: Instrument,
        timeframe: str,
        count: int,
    ) -> MarketSnapshot:
        raise NotImplementedError
