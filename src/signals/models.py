from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.data.models import Instrument


class SignalState(str, Enum):
    GENERATED = "GENERATED"
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    SKIPPED = "SKIPPED"


class SignalOutcome(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    DRAW = "DRAW"
    PENDING = "PENDING"
    SKIPPED = "SKIPPED"


class PaperSignal(BaseModel):
    id: str
    instrument: Instrument
    timeframe: str
    timestamp: datetime
    entry_price: float
    direction: str
    confidence: float = Field(ge=0.0, le=1.0)
    data_quality: str = "unknown"
    expiry_periods: int = 1
    expiry_timestamp: datetime | None = None
    chart_path: str | None = None
    state: SignalState = SignalState.GENERATED
    outcome: SignalOutcome = SignalOutcome.PENDING
    exit_price: float | None = None
    resolved_at: datetime | None = None
    price_change: float | None = None
    reason: str = ""
    rsi: float | None = None
    ema_fast: float | None = None
    ema_slow: float | None = None
    trend: str = "NEUTRAL"
    momentum: str = "NEUTRAL"
    volatility: str = "NEUTRAL"
    price_action: str = "NEUTRAL"
    telegram_sent: bool = False
    telegram_result_sent: bool = False
    raw_features: dict[str, Any] = Field(default_factory=dict)


class SignalLedger(BaseModel):
    signals: list[PaperSignal] = Field(default_factory=list)

    def add(self, signal: PaperSignal) -> None:
        self.signals.append(signal)

    def pending(self) -> list[PaperSignal]:
        return [s for s in self.signals if s.state == SignalState.PENDING]

    def by_instrument(self, instrument: Instrument) -> list[PaperSignal]:
        return [s for s in self.signals if s.instrument.symbol == instrument.symbol]

    def get_by_id(self, signal_id: str) -> PaperSignal | None:
        for s in self.signals:
            if s.id == signal_id:
                return s
        return None
