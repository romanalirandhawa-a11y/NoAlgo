from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.analysis.engine import AnalysisEngine
from src.data.models import AnalysisResult, Candle, Instrument
from src.market.live_service import LiveMarketDataService


@dataclass(frozen=True)
class LiveAnalysisResult:
    instrument: Instrument
    timeframe: str
    timestamp: datetime
    latest_price: float
    analysis: AnalysisResult
    candles: list[Candle]


class LiveAnalysisService:
    def __init__(self, market_service: LiveMarketDataService, analysis_engine: AnalysisEngine) -> None:
        self.market_service = market_service
        self.analysis_engine = analysis_engine

    async def analyze(self, instrument: Instrument, timeframe: str, count: int = 30) -> LiveAnalysisResult:
        snapshot = await self.market_service.get_snapshot(instrument, timeframe, count)
        analysis = await self.analysis_engine.analyze(snapshot)
        latest_price = snapshot.current_tick.last if snapshot.current_tick else snapshot.candles[-1].close if snapshot.candles else 0.0
        return LiveAnalysisResult(
            instrument=instrument,
            timeframe=timeframe,
            timestamp=snapshot.timestamp,
            latest_price=latest_price,
            analysis=analysis,
            candles=snapshot.candles,
        )
