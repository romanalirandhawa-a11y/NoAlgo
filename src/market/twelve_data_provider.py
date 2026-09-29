from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from src.data.models import Candle, Instrument, MarketSnapshot, MarketTick
from src.market.provider import MarketDataProvider
from src.utils.time import utc_now

logger = logging.getLogger(__name__)


class MarketDataError(Exception):
    pass


class TwelveDataProvider(MarketDataProvider):
    BASE_URL = "https://api.twelvedata.com/time_series"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._symbol_map: dict[str, str] = {
            "EUR/USD": "EUR/USD",
            "GBP/USD": "GBP/USD",
            "USD/JPY": "USD/JPY",
            "AUD/USD": "AUD/USD",
        }

    async def get_tick(self, instrument: Instrument) -> MarketTick:
        candles = await self.get_candles(instrument, "M1", 1)
        if not candles:
            raise MarketDataError("No tick data available")
        last = candles[-1]
        now = utc_now()
        spread = 0.0001 if instrument.symbol not in self._symbol_map else 0.00015
        base = last.close
        bid = round(base - spread / 2, 5)
        ask = round(base + spread / 2, 5)
        return MarketTick(
            instrument=instrument,
            timestamp=now,
            bid=bid,
            ask=ask,
            last=base,
        )

    async def get_candles(
        self,
        instrument: Instrument,
        timeframe: str,
        count: int,
        end_time: datetime | None = None,
    ) -> list[Candle]:
        if timeframe not in {"M1"}:
            raise MarketDataError(f"Unsupported timeframe: {timeframe}")
        if instrument.symbol not in self._symbol_map:
            raise MarketDataError(f"Unsupported instrument: {instrument.symbol}")
        symbol = self._symbol_map[instrument.symbol]
        params = {
            "symbol": symbol,
            "interval": "1min",
            "outputsize": str(max(1, count)),
            "apikey": self.api_key,
            "timezone": "UTC",
        }
        raw = await self._request(params)
        values = raw.get("values")
        if not isinstance(values, list):
            note = raw.get("message") or raw.get("Error Message") or "empty response"
            raise MarketDataError(f"Twelve Data error: {note}")
        candles = self._parse_series(instrument, timeframe, values)
        return candles[-count:] if candles else []

    async def get_snapshot(
        self,
        instrument: Instrument,
        timeframe: str,
        count: int,
    ) -> MarketSnapshot:
        candles = await self.get_candles(instrument, timeframe, count)
        tick = None
        if candles:
            tick = await self.get_tick(instrument)
        return MarketSnapshot(
            instrument=instrument,
            timestamp=utc_now(),
            candles=candles,
            current_tick=tick,
        )

    def _parse_series(
        self,
        instrument: Instrument,
        timeframe: str,
        values: list[dict[str, Any]],
    ) -> list[Candle]:
        parsed: list[Candle] = []
        for item in values:
            try:
                ts = datetime.strptime(item["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                parsed.append(
                    Candle(
                        instrument=instrument,
                        timestamp=ts,
                        timeframe=timeframe,
                        open=float(item["open"]),
                        high=float(item["high"]),
                        low=float(item["low"]),
                        close=float(item["close"]),
                    )
                )
            except (KeyError, ValueError) as exc:
                logger.debug("Skipping Twelve Data candle row: %s", exc)
        parsed = sorted(parsed, key=lambda c: c.timestamp)
        return parsed

    async def _request(self, params: dict[str, str]) -> dict[str, Any]:
        import httpx

        timeout = 10.0
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(self.BASE_URL, params=params)
                    if response.status_code == 429:
                        wait = 2 ** attempt
                        logger.warning("Twelve Data rate limited, retrying in %ss", wait)
                        await asyncio.sleep(wait)
                        continue
                    response.raise_for_status()
                    return dict(response.json())
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response else None
                if status and 500 <= status < 600 and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise MarketDataError(f"HTTP error {status}") from exc
            except httpx.RequestError as exc:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise MarketDataError(f"Network error: {exc}") from exc
        raise MarketDataError("Twelve Data request failed after retries")
