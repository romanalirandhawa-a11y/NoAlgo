from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from src.analysis.engine import AnalysisEngine
from src.analysis.live_analysis import LiveAnalysisService
from src.charts.generator import ChartGenerator
from src.config.constants import SUPPORTED_INSTRUMENTS
from src.data.models import AnalysisResult, Instrument
from src.market.live_service import LiveMarketDataService
from src.signals.ledger import SignalLedgerStore
from src.signals.models import PaperSignal, SignalOutcome, SignalState
from src.telegram.formatter import TelegramFormatter
from src.utils.time import utc_now

logger = logging.getLogger(__name__)


class SchedulerError(Exception):
    pass


class LiveSignalScheduler:
    def __init__(
        self,
        market_service: LiveMarketDataService,
        analysis_engine: AnalysisEngine,
        live_analysis: LiveAnalysisService,
        chart_generator: ChartGenerator,
        ledger: SignalLedgerStore,
        formatter: TelegramFormatter,
        send_callback: Callable[[str], None],
        instruments: list[str] | None = None,
        interval_seconds: int = 60,
        expiry_periods: int = 1,
        confidence_threshold: float = 0.7,
        enabled: bool = False,
    ) -> None:
        self.market_service = market_service
        self.analysis_engine = analysis_engine
        self.live_analysis = live_analysis
        self.chart_generator = chart_generator
        self.ledger = ledger
        self.formatter = formatter
        self.send_callback = send_callback
        self.instruments = instruments or SUPPORTED_INSTRUMENTS
        self.interval_seconds = max(1, interval_seconds)
        self.expiry_periods = expiry_periods
        self.confidence_threshold = confidence_threshold
        self.enabled = enabled
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._last_candle_ts: dict[str, datetime] = {}
        self._last_activity: datetime | None = None

    def start(self) -> None:
        if self._running:
            return
        if not self.enabled:
            logger.info("Live signal scheduler is disabled")
            return
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._run())
        except RuntimeError:
            pass
        logger.info("Live signal scheduler started")

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Live signal scheduler stopped")

    def is_running(self) -> bool:
        return self._running and self.enabled

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "running": self._running,
            "instruments": self.instruments,
            "interval_seconds": self.interval_seconds,
            "expiry_periods": self.expiry_periods,
            "confidence_threshold": self.confidence_threshold,
            "last_activity": self._last_activity.isoformat() if self._last_activity else None,
            "pending_signals": len(self.ledger.pending()),
            "last_candle_ts": {k: v.isoformat() for k, v in self._last_candle_ts.items()},
        }

    async def _run(self) -> None:
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("Scheduler tick failed: %s", exc)
            await asyncio.sleep(self.interval_seconds)

    async def _tick(self) -> None:
        if not self.enabled:
            return
        for symbol in self.instruments:
            if not self._running:
                return
            try:
                await self._process_instrument(symbol)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("Instrument processing failed for %s: %s", symbol, exc)

    async def _process_instrument(self, symbol: str) -> None:
        instrument = Instrument(symbol=symbol)
        result = await self.live_analysis.analyze(instrument, "M1", count=100)
        candles = result.candles
        if not candles:
            logger.debug("No candles for %s", symbol)
            return

        latest_candle = candles[-1]
        last_ts = self._last_candle_ts.get(symbol)
        if last_ts is not None and latest_candle.timestamp <= last_ts:
            logger.debug("No new candle for %s", symbol)
            return

        self._last_candle_ts[symbol] = latest_candle.timestamp
        self._last_activity = utc_now()

        analysis = result.analysis
        if self._should_skip(analysis):
            if analysis.direction == "NEUTRAL":
                logger.debug("Skipping %s: NEUTRAL direction", symbol)
            elif analysis.data_quality == "INSUFFICIENT":
                logger.debug("Skipping %s: INSUFFICIENT data quality", symbol)
            else:
                logger.debug(
                    "Skipping %s: confidence %.2f below threshold %.2f",
                    symbol,
                    analysis.confidence,
                    self.confidence_threshold,
                )
            return

        chart_path = None
        try:
            chart_path = self.chart_generator.generate_candlestick_chart(
                candles=candles,
                instrument=instrument,
                analysis_time=latest_candle.timestamp,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Chart generation failed for %s: %s", symbol, exc)

        signal = PaperSignal(
            id=f"{symbol}_{latest_candle.timestamp.strftime('%Y%m%d%H%M%S')}",
            instrument=instrument,
            timeframe="M1",
            timestamp=latest_candle.timestamp,
            entry_price=latest_candle.close,
            direction=analysis.direction,
            confidence=analysis.confidence,
            data_quality=analysis.data_quality,
            expiry_periods=self.expiry_periods,
            expiry_timestamp=latest_candle.timestamp + timedelta(minutes=self.expiry_periods),
            state=SignalState.PENDING,
            outcome=SignalOutcome.PENDING,
            chart_path=chart_path,
            rsi=analysis.rsi,
            ema_fast=analysis.ema_fast,
            ema_slow=analysis.ema_slow,
            trend=analysis.trend,
            momentum=analysis.momentum,
            volatility=analysis.volatility,
            price_action=analysis.price_action,
            raw_features=dict(analysis.features),
        )
        self.ledger.add_signal(signal)
        logger.info(
            "Paper signal created: %s %s %s entry=%s confidence=%.2f",
            symbol,
            signal.id,
            analysis.direction,
            signal.entry_price,
            analysis.confidence,
        )

        text = self.formatter.format_signal(signal, result.latest_price)
        try:
            self.send_callback(text)
            self.ledger.update_signal(signal.id, telegram_sent=True)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send signal Telegram message for %s: %s", symbol, exc)

        await self._resolve_pending_signals(instrument)

    async def _resolve_pending_signals(self, instrument: Instrument) -> None:
        pending = [s for s in self.ledger.pending() if s.instrument.symbol == instrument.symbol]
        if not pending:
            return

        result = await self.live_analysis.analyze(instrument, "M1", count=100)
        candles = result.candles
        if not candles:
            return

        candle_ts_map = {c.timestamp: c for c in candles}
        for signal in pending:
            if signal.expiry_timestamp is None:
                continue
            if signal.expiry_timestamp not in candle_ts_map:
                continue
            exit_candle = candle_ts_map[signal.expiry_timestamp]
            outcome = self._determine_outcome(signal.direction, exit_candle.close - signal.entry_price)
            self.ledger.update_signal(
                signal.id,
                state=SignalState.RESOLVED,
                outcome=outcome,
                exit_price=exit_candle.close,
                resolved_at=utc_now(),
                price_change=round(exit_candle.close - signal.entry_price, 5),
            )
            logger.info(
                "Paper signal resolved: %s %s outcome=%s exit=%s",
                signal.instrument.symbol,
                signal.id,
                outcome.value,
                exit_candle.close,
            )

    def _should_skip(self, analysis: AnalysisResult) -> bool:
        if analysis.direction == "NEUTRAL":
            return True
        if analysis.data_quality == "INSUFFICIENT":
            return True
        return analysis.confidence < self.confidence_threshold

    def _determine_outcome(self, direction: str, price_change: float) -> SignalOutcome:
        if direction == "BULLISH":
            if price_change > 0:
                return SignalOutcome.WIN
            if price_change < 0:
                return SignalOutcome.LOSS
            return SignalOutcome.DRAW
        if direction == "BEARISH":
            if price_change < 0:
                return SignalOutcome.WIN
            if price_change > 0:
                return SignalOutcome.LOSS
            return SignalOutcome.DRAW
        return SignalOutcome.SKIPPED
