from __future__ import annotations

from datetime import datetime, timezone

from src.data.models import Instrument
from src.signals.models import PaperSignal, SignalLedger, SignalOutcome, SignalState


def _instrument() -> Instrument:
    return Instrument(symbol="EUR/USD")


def _signal(ts: datetime | None = None) -> PaperSignal:
    ts = ts or datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    return PaperSignal(
        id="sig1",
        instrument=_instrument(),
        timeframe="M1",
        timestamp=ts,
        entry_price=1.0,
        direction="BULLISH",
        confidence=0.8,
        state=SignalState.PENDING,
        outcome=SignalOutcome.PENDING,
    )


def test_signal_ledger_add() -> None:
    ledger = SignalLedger()
    signal = _signal()
    ledger.add(signal)
    assert len(ledger.signals) == 1
    assert ledger.signals[0].id == "sig1"


def test_signal_ledger_pending() -> None:
    ledger = SignalLedger()
    ledger.add(_signal())
    resolved = PaperSignal(
        id="sig2",
        instrument=_instrument(),
        timeframe="M1",
        timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc),
        entry_price=1.0,
        direction="BEARISH",
        confidence=0.9,
        state=SignalState.RESOLVED,
        outcome=SignalOutcome.WIN,
    )
    ledger.add(resolved)
    assert len(ledger.pending()) == 1
    assert ledger.pending()[0].id == "sig1"


def test_signal_ledger_by_instrument() -> None:
    ledger = SignalLedger()
    ledger.add(_signal())
    usdjpy = Instrument(symbol="USD/JPY")
    signal2 = PaperSignal(
        id="sig2",
        instrument=usdjpy,
        timeframe="M1",
        timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc),
        entry_price=1.0,
        direction="BEARISH",
        confidence=0.9,
        state=SignalState.PENDING,
        outcome=SignalOutcome.PENDING,
    )
    ledger.add(signal2)
    eurusd_signals = ledger.by_instrument(_instrument())
    assert len(eurusd_signals) == 1
    assert eurusd_signals[0].id == "sig1"


def test_signal_ledger_get_by_id() -> None:
    ledger = SignalLedger()
    ledger.add(_signal())
    found = ledger.get_by_id("sig1")
    assert found is not None
    assert found.id == "sig1"
    assert ledger.get_by_id("missing") is None


def test_signal_defaults() -> None:
    signal = _signal()
    assert signal.state == SignalState.PENDING
    assert signal.outcome == SignalOutcome.PENDING
    assert signal.expiry_periods == 1
    assert signal.chart_path is None
    assert signal.exit_price is None
    assert signal.resolved_at is None
    assert signal.price_change is None
    assert signal.telegram_sent is False
    assert signal.telegram_result_sent is False
    assert signal.raw_features == {}
