from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.data.models import Instrument
from src.signals.ledger import SignalLedgerStore
from src.signals.models import PaperSignal, SignalOutcome, SignalState


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


def test_ledger_store_persists_and_loads(tmp_path: Path) -> None:
    store = SignalLedgerStore(output_dir=tmp_path)
    store.add_signal(_signal())
    path = tmp_path / "signals.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["signals"][0]["id"] == "sig1"

    store2 = SignalLedgerStore(output_dir=tmp_path)
    assert len(store2.all()) == 1
    assert store2.get_by_id("sig1") is not None


def test_ledger_store_update(tmp_path: Path) -> None:
    store = SignalLedgerStore(output_dir=tmp_path)
    store.add_signal(_signal())
    updated = store.update_signal("sig1", state=SignalState.RESOLVED, outcome=SignalOutcome.WIN, exit_price=1.001)
    assert updated is not None
    assert updated.state == SignalState.RESOLVED
    assert updated.outcome == SignalOutcome.WIN
    assert updated.exit_price == 1.001
    reloaded = store.get_by_id("sig1")
    assert reloaded is not None
    assert reloaded.state == SignalState.RESOLVED


def test_ledger_store_corrupted_file_fails_safely(tmp_path: Path) -> None:
    path = tmp_path / "signals.json"
    path.write_text("not json", encoding="utf-8")
    store = SignalLedgerStore(output_dir=tmp_path)
    assert len(store.all()) == 0
    store.add_signal(_signal())
    assert len(store.all()) == 1


def test_ledger_store_signal_fields_complete(tmp_path: Path) -> None:
    store = SignalLedgerStore(output_dir=tmp_path)
    ts = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    signal = PaperSignal(
        id="sig_fields",
        instrument=_instrument(),
        timeframe="M1",
        timestamp=ts,
        entry_price=1.17300,
        direction="BULLISH",
        confidence=0.82,
        data_quality="GOOD",
        expiry_periods=1,
        expiry_timestamp=ts + timedelta(minutes=1),
        state=SignalState.PENDING,
        outcome=SignalOutcome.PENDING,
        chart_path="/tmp/chart.png",
        rsi=60.0,
        ema_fast=1.1732,
        ema_slow=1.1730,
        trend="BULLISH",
        momentum="POSITIVE",
        volatility="NORMAL",
        price_action="BULLISH",
    )
    store.add_signal(signal)
    loaded = store.get_by_id("sig_fields")
    assert loaded is not None
    assert loaded.entry_price == 1.17300
    assert loaded.direction == "BULLISH"
    assert loaded.confidence == 0.82
    assert loaded.data_quality == "GOOD"
    assert loaded.expiry_periods == 1
    assert loaded.state == SignalState.PENDING
    assert loaded.outcome == SignalOutcome.PENDING
    assert loaded.chart_path == "/tmp/chart.png"
    assert loaded.rsi == 60.0
    assert loaded.ema_fast == 1.1732
    assert loaded.ema_slow == 1.1730
    updated = store.update_signal("sig_fields", state=SignalState.RESOLVED, outcome=SignalOutcome.WIN, exit_price=1.17350)
    assert updated is not None
    assert updated.entry_price == 1.17300
    assert updated.exit_price == 1.17350
    reloaded = store.get_by_id("sig_fields")
    assert reloaded is not None
    assert reloaded.entry_price == 1.17300
    assert reloaded.exit_price == 1.17350


def test_ledger_store_stats(tmp_path: Path) -> None:
    store = SignalLedgerStore(output_dir=tmp_path)
    store.add_signal(_signal())
    resolved = PaperSignal(
        id="sig2",
        instrument=_instrument(),
        timeframe="M1",
        timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc),
        entry_price=1.0,
        direction="BULLISH",
        confidence=0.8,
        state=SignalState.RESOLVED,
        outcome=SignalOutcome.WIN,
    )
    store.add_signal(resolved)
    stats = store.stats()
    assert stats["total"] == 2
    assert stats["pending"] == 1
    assert stats["resolved"] == 1
    assert stats["wins"] == 1
