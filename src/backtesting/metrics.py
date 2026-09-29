from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from src.backtesting.models import BacktestMetrics, BacktestOutcome, BacktestResult


def compute_metrics(results: list[BacktestResult], candles_loaded: int = 0, dataset_start: datetime | None = None, dataset_end: datetime | None = None, data_gaps_detected: bool = False) -> BacktestMetrics:
    total_opportunities = len(results)
    total_signals = sum(1 for r in results if r.outcome not in (BacktestOutcome.SKIPPED, BacktestOutcome.PENDING))
    total_skipped = sum(1 for r in results if r.outcome == BacktestOutcome.SKIPPED)
    total_wins = sum(1 for r in results if r.outcome == BacktestOutcome.WIN)
    total_losses = sum(1 for r in results if r.outcome == BacktestOutcome.LOSS)
    total_draws = sum(1 for r in results if r.outcome == BacktestOutcome.DRAW)
    total_pending = sum(1 for r in results if r.outcome == BacktestOutcome.PENDING)

    resolved = [r for r in results if r.outcome in (BacktestOutcome.WIN, BacktestOutcome.LOSS, BacktestOutcome.DRAW)]
    resolved_count = len(resolved)
    win_rate = (total_wins / resolved_count) if resolved_count else None
    loss_rate = (total_losses / resolved_count) if resolved_count else None
    draw_rate = (total_draws / resolved_count) if resolved_count else None

    signal_results = [r for r in results if r.outcome not in (BacktestOutcome.SKIPPED, BacktestOutcome.PENDING)]
    confidences = [r.signal.confidence for r in signal_results]
    average_confidence = sum(confidences) / len(confidences) if confidences else None

    win_confidences = [r.signal.confidence for r in results if r.outcome == BacktestOutcome.WIN]
    loss_confidences = [r.signal.confidence for r in results if r.outcome == BacktestOutcome.LOSS]
    average_confidence_wins = sum(win_confidences) / len(win_confidences) if win_confidences else None
    average_confidence_losses = sum(loss_confidences) / len(loss_confidences) if loss_confidences else None

    max_consecutive_wins = 0
    max_consecutive_losses = 0
    current_wins = 0
    current_losses = 0
    for r in results:
        if r.outcome == BacktestOutcome.WIN:
            current_wins += 1
            max_consecutive_wins = max(max_consecutive_wins, current_wins)
            current_losses = 0
        elif r.outcome == BacktestOutcome.LOSS:
            current_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, current_losses)
            current_wins = 0
        else:
            current_wins = 0
            current_losses = 0

    buckets = _confidence_buckets(signal_results)
    session_breakdown = _session_breakdown(results)

    return BacktestMetrics(
        dataset_start=dataset_start,
        dataset_end=dataset_end,
        candles_loaded=candles_loaded,
        candles_used=sum(1 for r in results if r.outcome != BacktestOutcome.SKIPPED) + total_skipped,
        total_opportunities=total_opportunities,
        total_signals=total_signals,
        total_skipped=total_skipped,
        total_wins=total_wins,
        total_losses=total_losses,
        total_draws=total_draws,
        total_pending=total_pending,
        win_rate=win_rate,
        loss_rate=loss_rate,
        draw_rate=draw_rate,
        average_confidence=average_confidence,
        average_confidence_wins=average_confidence_wins,
        average_confidence_losses=average_confidence_losses,
        max_consecutive_wins=max_consecutive_wins,
        max_consecutive_losses=max_consecutive_losses,
        confidence_buckets=buckets,
        session_breakdown=session_breakdown,
        data_gaps_detected=data_gaps_detected,
    )


def _confidence_buckets(signal_results: list[BacktestResult]) -> dict[str, dict[str, int | float | None]]:
    bucket_ranges = [
        ("50-59", 0.50, 0.60),
        ("60-69", 0.60, 0.70),
        ("70-79", 0.70, 0.80),
        ("80-89", 0.80, 0.90),
        ("90-100", 0.90, 1.01),
    ]
    buckets: dict[str, dict[str, int | float | None]] = {}
    for name, low, high in bucket_ranges:
        items = [r for r in signal_results if low <= r.signal.confidence < high]
        wins = sum(1 for r in items if r.outcome == BacktestOutcome.WIN)
        losses = sum(1 for r in items if r.outcome == BacktestOutcome.LOSS)
        draws = sum(1 for r in items if r.outcome == BacktestOutcome.DRAW)
        total = len(items)
        win_rate = (wins / total) if total else None
        buckets[name] = {
            "signals": total,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_rate": win_rate,
        }
    return buckets


def _session_breakdown(results: list[BacktestResult]) -> dict[str, dict[str, int | float | None]]:
    session_data: dict[str, list[BacktestResult]] = defaultdict(list)
    for r in results:
        if r.outcome in (BacktestOutcome.WIN, BacktestOutcome.LOSS, BacktestOutcome.DRAW):
            hour = r.signal.timestamp.strftime("%H")
            session_data[hour].append(r)
    breakdown: dict[str, dict[str, int | float | None]] = {}
    for hour, items in sorted(session_data.items()):
        wins = sum(1 for r in items if r.outcome == BacktestOutcome.WIN)
        losses = sum(1 for r in items if r.outcome == BacktestOutcome.LOSS)
        draws = sum(1 for r in items if r.outcome == BacktestOutcome.DRAW)
        total = len(items)
        win_rate = (wins / total) if total else None
        breakdown[f"hour_{hour}"] = {
            "signals": total,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_rate": win_rate,
        }
    return breakdown
