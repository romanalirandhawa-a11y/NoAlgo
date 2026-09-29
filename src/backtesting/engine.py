from __future__ import annotations

from src.analysis.engine import AnalysisEngine
from src.backtesting.models import BacktestConfig, BacktestOutcome, BacktestResult, BacktestSignal
from src.data.models import AnalysisResult, Candle, MarketSnapshot


class BacktestError(Exception):
    pass


class BacktestEngine:
    def __init__(self, analysis_engine: AnalysisEngine) -> None:
        self.analysis_engine = analysis_engine

    async def run(self, candles: list[Candle], config: BacktestConfig) -> list[BacktestResult]:
        if len(candles) < config.minimum_candles + config.expiry_periods:
            return []

        results: list[BacktestResult] = []
        for i in range(config.minimum_candles - 1, len(candles) - config.expiry_periods):
            if config.start_index and i < config.start_index:
                continue
            snapshot_candles = candles[: i + 1]
            snapshot = MarketSnapshot(
                instrument=config.instrument,
                timestamp=snapshot_candles[-1].timestamp,
                candles=snapshot_candles,
            )
            analysis = await self.analysis_engine.analyze(snapshot)
            if self._should_skip(analysis, config.confidence_threshold):
                results.append(
                    BacktestResult(
                        signal=BacktestSignal(
                            timestamp=analysis.timestamp,
                            instrument=config.instrument,
                            timeframe=config.timeframe,
                            entry_price=snapshot_candles[-1].close,
                            direction=analysis.direction,
                            confidence=analysis.confidence,
                            data_quality=analysis.data_quality,
                            rsi=analysis.rsi,
                            ema_fast=analysis.ema_fast,
                            ema_slow=analysis.ema_slow,
                            trend=analysis.trend,
                            momentum=analysis.momentum,
                            volatility=analysis.volatility,
                            price_action=analysis.price_action,
                        ),
                        outcome=BacktestOutcome.SKIPPED,
                        reason="neutral_or_low_confidence",
                    )
                )
                continue

            entry_price = snapshot_candles[-1].close
            exit_candle = candles[i + config.expiry_periods]
            exit_price = exit_candle.close
            price_change = exit_price - entry_price
            outcome = self._determine_outcome(analysis.direction, price_change)

            results.append(
                BacktestResult(
                    signal=BacktestSignal(
                        timestamp=analysis.timestamp,
                        instrument=config.instrument,
                        timeframe=config.timeframe,
                        entry_price=entry_price,
                        direction=analysis.direction,
                        confidence=analysis.confidence,
                        data_quality=analysis.data_quality,
                        rsi=analysis.rsi,
                        ema_fast=analysis.ema_fast,
                        ema_slow=analysis.ema_slow,
                        trend=analysis.trend,
                        momentum=analysis.momentum,
                        volatility=analysis.volatility,
                        price_action=analysis.price_action,
                    ),
                    outcome=outcome,
                    exit_price=exit_price,
                    result_timestamp=exit_candle.timestamp,
                    price_change=price_change,
                    reason="",
                )
            )
        return results

    def _should_skip(self, analysis: AnalysisResult, confidence_threshold: float) -> bool:
        if analysis.direction == "NEUTRAL":
            return True
        return analysis.confidence < confidence_threshold

    def _determine_outcome(self, direction: str, price_change: float) -> BacktestOutcome:
        if direction == "BULLISH":
            if price_change > 0:
                return BacktestOutcome.WIN
            if price_change < 0:
                return BacktestOutcome.LOSS
            return BacktestOutcome.DRAW
        if direction == "BEARISH":
            if price_change < 0:
                return BacktestOutcome.WIN
            if price_change > 0:
                return BacktestOutcome.LOSS
            return BacktestOutcome.DRAW
        return BacktestOutcome.SKIPPED
