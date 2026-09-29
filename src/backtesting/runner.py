from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.backtesting.engine import BacktestEngine, BacktestError
from src.backtesting.metrics import compute_metrics
from src.backtesting.models import BacktestConfig, BacktestMetrics
from src.backtesting.reporter import format_report
from src.data.models import Candle

logger = logging.getLogger(__name__)


class BacktestRunner:
    def __init__(self, output_dir: str | Path = "data/backtests") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def run(self, candles: list[Candle], config: BacktestConfig) -> tuple[BacktestMetrics, str]:
        filtered = self._filter_candles(candles, config)
        if not filtered:
            raise BacktestError("No candles available after filtering")

        dataset_start = filtered[0].timestamp if filtered else None
        dataset_end = filtered[-1].timestamp if filtered else None
        data_gaps_detected = self._detect_gaps(filtered)

        from src.analysis.engine import AnalysisEngine

        engine = BacktestEngine(analysis_engine=AnalysisEngine())
        results = await engine.run(filtered, config)
        metrics = compute_metrics(
            results,
            candles_loaded=len(candles),
            dataset_start=dataset_start,
            dataset_end=dataset_end,
            data_gaps_detected=data_gaps_detected,
        )
        report = format_report(config, metrics)
        self._save_results(config, metrics, report)
        return metrics, report

    def _filter_candles(self, candles: list[Candle], config: BacktestConfig) -> list[Candle]:
        filtered = [c for c in candles if c.instrument.symbol == config.instrument.symbol]
        if config.start_time:
            filtered = [c for c in filtered if c.timestamp >= config.start_time]
        if config.end_time:
            filtered = [c for c in filtered if c.timestamp <= config.end_time]
        filtered.sort(key=lambda c: c.timestamp)
        return filtered

    def _detect_gaps(self, candles: list[Candle]) -> bool:
        if len(candles) < 2:
            return False
        for i in range(1, len(candles)):
            delta = (candles[i].timestamp - candles[i - 1].timestamp).total_seconds() / 60.0
            if delta > 1.5:
                return True
        return False

    def _save_results(self, config: BacktestConfig, metrics: BacktestMetrics, report: str) -> None:
        payload = {
            "instrument": str(config.instrument),
            "timeframe": config.timeframe,
            "expiry_periods": config.expiry_periods,
            "confidence_threshold": config.confidence_threshold,
            "start_time": config.start_time.isoformat() if config.start_time else None,
            "end_time": config.end_time.isoformat() if config.end_time else None,
            "metrics": metrics.model_dump(mode="json"),
            "report": report,
        }
        path = self.output_dir / f"backtest_{config.instrument.symbol.replace('/', '_')}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("Backtest results saved to %s", path)
