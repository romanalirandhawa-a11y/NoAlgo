from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from src.data.models import Instrument


class BacktestOutcome(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    DRAW = "DRAW"
    PENDING = "PENDING"
    SKIPPED = "SKIPPED"


class BacktestConfig(BaseModel):
    instrument: Instrument
    timeframe: str = "M1"
    expiry_periods: int = 1
    minimum_candles: int = 30
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    start_index: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None
    split_ratio: float | None = Field(default=None, ge=0.0, le=1.0)


class BacktestSignal(BaseModel):
    timestamp: datetime
    instrument: Instrument
    timeframe: str
    entry_price: float
    direction: str
    confidence: float = Field(ge=0.0, le=1.0)
    data_quality: str = "unknown"
    rsi: float | None = None
    ema_fast: float | None = None
    ema_slow: float | None = None
    trend: str = "NEUTRAL"
    momentum: str = "NEUTRAL"
    volatility: str = "NEUTRAL"
    price_action: str = "NEUTRAL"


class BacktestResult(BaseModel):
    signal: BacktestSignal
    outcome: BacktestOutcome
    exit_price: float | None = None
    result_timestamp: datetime | None = None
    price_change: float | None = None
    reason: str = ""


class BacktestMetrics(BaseModel):
    dataset_start: datetime | None = None
    dataset_end: datetime | None = None
    candles_loaded: int = 0
    candles_used: int = 0
    total_opportunities: int = 0
    total_signals: int = 0
    total_skipped: int = 0
    total_wins: int = 0
    total_losses: int = 0
    total_draws: int = 0
    total_pending: int = 0
    win_rate: float | None = None
    loss_rate: float | None = None
    draw_rate: float | None = None
    average_confidence: float | None = None
    average_confidence_wins: float | None = None
    average_confidence_losses: float | None = None
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    confidence_buckets: dict[str, dict[str, int | float | None]] = Field(default_factory=dict)
    session_breakdown: dict[str, dict[str, int | float | None]] = Field(default_factory=dict)
    data_gaps_detected: bool = False
