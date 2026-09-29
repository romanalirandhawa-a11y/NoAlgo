
from src.data.models import Direction, Instrument, TradeResult
from src.paper_trading.tracker import PaperTradeTracker


def test_create_trade() -> None:
    tracker = PaperTradeTracker()
    inst = Instrument(symbol="EUR/USD")
    trade = tracker.create_trade(
        instrument=inst,
        direction=Direction.BULLISH,
        entry_price=1.17300,
        expiry_seconds=60,
    )
    assert trade.result == TradeResult.PENDING
    assert trade.entry_price == 1.17300


def test_resolve_trade_profit() -> None:
    tracker = PaperTradeTracker()
    inst = Instrument(symbol="EUR/USD")
    trade = tracker.create_trade(
        instrument=inst,
        direction=Direction.BULLISH,
        entry_price=1.17300,
        expiry_seconds=60,
    )
    result = tracker.resolve_trade(trade, 1.17350)
    assert result.profit == 0.0005
    assert result.result == TradeResult.CORRECT


def test_resolve_trade_loss() -> None:
    tracker = PaperTradeTracker()
    inst = Instrument(symbol="EUR/USD")
    trade = tracker.create_trade(
        instrument=inst,
        direction=Direction.BEARISH,
        entry_price=1.17300,
        expiry_seconds=60,
    )
    result = tracker.resolve_trade(trade, 1.17350)
    assert result.profit == -0.0005
    assert result.result == TradeResult.INCORRECT
