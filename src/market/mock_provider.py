from __future__ import annotations

import random
from datetime import datetime, timedelta

from src.data.models import Candle, Instrument, MarketSnapshot, MarketTick
from src.market.provider import MarketDataProvider
from src.utils.time import utc_now


class MockMarketDataProvider(MarketDataProvider):
    def __init__(self, base_price: float = 1.17320) -> None:
        self.base_price = base_price
        self._last_close = base_price

    async def get_tick(self, instrument: Instrument) -> MarketTick:
        now = utc_now()
        drift = random.uniform(-0.0005, 0.0005)
        last = round(self._last_close + drift, 5)
        spread = 0.0001
        bid = round(last - spread / 2, 5)
        ask = round(last + spread / 2, 5)
        self._last_close = last
        return MarketTick(
            instrument=instrument,
            timestamp=now,
            bid=bid,
            ask=ask,
            last=last,
        )

    async def get_candles(
        self,
        instrument: Instrument,
        timeframe: str,
        count: int,
        end_time: datetime | None = None,
    ) -> list[Candle]:
        end = end_time or utc_now()
        candles: list[Candle] = []
        price = self._last_close
        for i in range(count):
            t = end - timedelta(minutes=count - i)
            change = random.uniform(-0.0010, 0.0010)
            open_price = price
            close = round(price + change, 5)
            high = round(max(open_price, close) + random.uniform(0, 0.0005), 5)
            low = round(min(open_price, close) - random.uniform(0, 0.0005), 5)
            candles.append(
                Candle(
                    instrument=instrument,
                    timestamp=t,
                    timeframe=timeframe,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                )
            )
            price = close
        self._last_close = price
        return candles

    async def get_snapshot(
        self,
        instrument: Instrument,
        timeframe: str,
        count: int,
    ) -> MarketSnapshot:
        candles = await self.get_candles(instrument, timeframe, count)
        tick = await self.get_tick(instrument)
        return MarketSnapshot(
            instrument=instrument,
            timestamp=utc_now(),
            candles=candles,
            current_tick=tick,
        )
