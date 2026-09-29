from __future__ import annotations

import uuid

from src.data.models import Direction, Instrument, PaperResult, PaperTrade, TradeResult
from src.utils.time import utc_now


class PaperTradeTracker:
    def __init__(self) -> None:
        self._trades: list[PaperTrade] = []

    def create_trade(
        self,
        instrument: Instrument,
        direction: str,
        entry_price: float,
        expiry_seconds: int,
    ) -> PaperTrade:
        trade = PaperTrade(
            id=str(uuid.uuid4()),
            instrument=instrument,
            timestamp=utc_now(),
            direction=direction,
            entry_price=entry_price,
            expiry_seconds=expiry_seconds,
        )
        self._trades.append(trade)
        return trade

    def resolve_trade(self, trade: PaperTrade, exit_price: float) -> PaperResult:
        profit = self._calculate_profit(trade, exit_price)
        result = TradeResult.CORRECT if profit > 0 else TradeResult.INCORRECT
        trade.result = result
        trade.exit_price = exit_price
        trade.resolved_at = utc_now()
        return PaperResult(
            instrument=trade.instrument,
            timestamp=utc_now(),
            direction=trade.direction,
            result=result,
            entry_price=trade.entry_price,
            exit_price=exit_price,
            profit=profit,
        )

    def _calculate_profit(self, trade: PaperTrade, exit_price: float) -> float:
        if trade.direction == Direction.BULLISH:
            return round(exit_price - trade.entry_price, 5)
        elif trade.direction == Direction.BEARISH:
            return round(trade.entry_price - exit_price, 5)
        return 0.0

    def get_trades(self) -> list[PaperTrade]:
        return list(self._trades)
