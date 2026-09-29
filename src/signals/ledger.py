from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.data.models import Instrument
from src.signals.models import PaperSignal, SignalLedger, SignalOutcome, SignalState

logger = logging.getLogger(__name__)


class SignalPersistenceError(Exception):
    pass


class SignalLedgerStore:
    def __init__(self, output_dir: str | Path = "data/paper_signals") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._ledger = SignalLedger()
        self._load()

    def _path(self) -> Path:
        return self.output_dir / "signals.json"

    def _load(self) -> None:
        path = self._path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "signals" in data:
                self._ledger = SignalLedger.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load signal ledger: %s", exc)
            self._ledger = SignalLedger()

    def save(self) -> None:
        path = self._path()
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(self._ledger.model_dump(mode="json"), indent=2), encoding="utf-8")
            tmp.replace(path)
        except Exception as exc:
            raise SignalPersistenceError(f"Failed to save signal ledger: {exc}") from exc

    def add_signal(self, signal: PaperSignal) -> None:
        self._ledger.add(signal)
        self.save()
        logger.info("Signal persisted: %s", signal.id)

    def update_signal(self, signal_id: str, **changes: Any) -> PaperSignal | None:
        signal = self._ledger.get_by_id(signal_id)
        if not signal:
            return None
        updated = signal.model_copy(update=changes)
        for idx, s in enumerate(self._ledger.signals):
            if s.id == signal_id:
                self._ledger.signals[idx] = updated
                break
        self.save()
        return updated

    def pending(self) -> list[PaperSignal]:
        return self._ledger.pending()

    def by_instrument(self, instrument: Instrument) -> list[PaperSignal]:
        return self._ledger.by_instrument(instrument)

    def get_by_id(self, signal_id: str) -> PaperSignal | None:
        return self._ledger.get_by_id(signal_id)

    def all(self) -> list[PaperSignal]:
        return list(self._ledger.signals)

    def stats(self) -> dict[str, int]:
        signals = self._ledger.signals
        resolved = [s for s in signals if s.state == SignalState.RESOLVED]
        wins = sum(1 for s in resolved if s.outcome == SignalOutcome.WIN)
        losses = sum(1 for s in resolved if s.outcome == SignalOutcome.LOSS)
        draws = sum(1 for s in resolved if s.outcome == SignalOutcome.DRAW)
        pending = sum(1 for s in signals if s.state == SignalState.PENDING)
        return {
            "total": len(signals),
            "pending": pending,
            "resolved": len(resolved),
            "wins": wins,
            "losses": losses,
            "draws": draws,
        }
