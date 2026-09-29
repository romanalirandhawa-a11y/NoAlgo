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


class AlphaVantageProvider(MarketDataProvider):
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._last_tick_prices: dict[str, float] = {}
        self._symbol_map: dict[str, tuple[str, str]] = {
            "EUR/USD": ("EUR", "USD"),
            "GBP/USD": ("GBP", "USD"),
            "USD/JPY": ("USD", "JPY"),
            "AUD/USD": ("AUD", "USD"),
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
        from_symbol, to_symbol = self._symbol_map[instrument.symbol]
        params = {
            "function": "FX_INTRADAY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "interval": "1min",
            "apikey": self.api_key,
            "outputsize": "compact",
        }
        raw = await self._request(params)
        key = "Time Series FX (1min)"
        series = raw.get(key)
        if not isinstance(series, dict):
            note = raw.get("Note") or raw.get("Error Message") or "empty response"
            raise MarketDataError(f"Alpha Vantage error: {note}")
        candles = self._parse_series(instrument, timeframe, series, count)
        return candles

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
        series: dict[str, Any],
        count: int,
    ) -> list[Candle]:
        parsed: list[Candle] = []
        for ts_str, values in series.items():
            try:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                parsed.append(
                    Candle(
                        instrument=instrument,
                        timestamp=ts,
                        timeframe=timeframe,
                        open=float(values["1. open"]),
                        high=float(values["2. high"]),
                        low=float(values["3. low"]),
                        close=float(values["4. close"]),
                    )
                )
            except (KeyError, ValueError) as exc:
                logger.debug("Skipping candle row %s: %s", ts_str, exc)
        parsed = sorted(parsed, key=lambda c: c.timestamp)
        return parsed[-count:] if parsed else []

    async def _request(self, params: dict[str, str]) -> dict[str, Any]:
        import httpx

        timeout = 10.0
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(self.BASE_URL, params=params)
                    if response.status_code == 429:
                        wait = 2 ** attempt
                        logger.warning("Alpha Vantage rate limited, retrying in %ss", wait)
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
        raise MarketDataError("Alpha Vantage request failed after retries")
