from __future__ import annotations

from src.backtesting.models import BacktestConfig, BacktestMetrics


def format_report(config: BacktestConfig, metrics: BacktestMetrics) -> str:
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        "📊 BACKTEST REPORT",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        f"Market: {config.instrument}",
        f"TF: {config.timeframe}",
        f"Expiry: {config.expiry_periods} candle",
        "",
        f"Dataset: {metrics.dataset_start.strftime('%Y-%m-%d %H:%M UTC') if metrics.dataset_start else 'N/A'} -> {metrics.dataset_end.strftime('%Y-%m-%d %H:%M UTC') if metrics.dataset_end else 'N/A'}",
        f"Candles loaded: {metrics.candles_loaded}",
        "",
        f"Signals: {metrics.total_signals}",
        f"Skipped: {metrics.total_skipped}",
        "",
        f"✅ Wins: {metrics.total_wins}",
        f"❌ Losses: {metrics.total_losses}",
        f"➖ Draws: {metrics.total_draws}",
        f"⏳ Pending: {metrics.total_pending}",
        "",
        f"Win Rate: {metrics.win_rate:.2%}" if metrics.win_rate is not None else "Win Rate: N/A",
        "",
        f"Average Confidence: {metrics.average_confidence:.2%}" if metrics.average_confidence is not None else "Average Confidence: N/A",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        "CONFIDENCE BUCKETS",
        "",
    ]
    for bucket_name, bucket_data in metrics.confidence_buckets.items():
        signals = bucket_data.get("signals", 0)
        wins = bucket_data.get("wins", 0)
        losses = bucket_data.get("losses", 0)
        draws = bucket_data.get("draws", 0)
        win_rate = bucket_data.get("win_rate")
        win_rate_text = f"{win_rate:.2%}" if win_rate is not None else "N/A"
        lines.append(f"{bucket_name}%: signals={signals}, wins={wins}, losses={losses}, draws={draws}, win_rate={win_rate_text}")
    if metrics.session_breakdown:
        lines.extend(
            [
                "",
                "━━━━━━━━━━━━━━━━━━━━",
                "",
                "SESSION BREAKDOWN",
                "",
            ]
        )
        for session, data in metrics.session_breakdown.items():
            signals = data.get("signals", 0)
            wins = data.get("wins", 0)
            losses = data.get("losses", 0)
            draws = data.get("draws", 0)
            win_rate = data.get("win_rate")
            win_rate_text = f"{win_rate:.2%}" if win_rate is not None else "N/A"
            lines.append(f"{session}: signals={signals}, wins={wins}, losses={losses}, draws={draws}, win_rate={win_rate_text}")
    lines.extend(
        [
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            "Historical evaluation only.",
            "Confidence represents feature agreement,",
            "not probability of profit.",
        ]
    )
    return "\n".join(lines)

