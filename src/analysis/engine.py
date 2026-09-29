from __future__ import annotations

from src.analysis.features import (
    AnalysisError,
    assess_data_quality,
    compute_confidence,
    compute_overall_bias,
    extract_features,
)
from src.data.models import AnalysisResult, MarketSnapshot


class AnalysisEngine:
    def __init__(self) -> None:
        pass

    async def analyze(self, snapshot: MarketSnapshot) -> AnalysisResult:
        candles = snapshot.candles
        if not candles:
            return AnalysisResult(
                instrument=snapshot.instrument,
                timestamp=snapshot.timestamp,
                direction="NEUTRAL",
                confidence=0.0,
                reason="No data available",
                data_quality="INSUFFICIENT",
            )

        now_index = len(candles) - 1
        data_quality = assess_data_quality(candles)
        try:
            features = extract_features(candles, now_index)
        except AnalysisError as exc:
            return AnalysisResult(
                instrument=snapshot.instrument,
                timestamp=snapshot.timestamp,
                direction="NEUTRAL",
                confidence=0.0,
                reason=f"Analysis error: {exc}",
                data_quality="INSUFFICIENT",
            )

        overall_bias = compute_overall_bias(features)
        confidence = compute_confidence(features)

        return AnalysisResult(
            instrument=snapshot.instrument,
            timestamp=snapshot.timestamp,
            direction=overall_bias,
            confidence=confidence,
            reason="Feature-based analysis",
            features={
                "rsi": features.get("rsi"),
                "ema_fast": features.get("ema_fast"),
                "ema_slow": features.get("ema_slow"),
                "momentum_value": features.get("momentum_value"),
                "atr": features.get("atr"),
                "trend": features.get("trend"),
                "momentum": features.get("momentum"),
                "volatility": features.get("volatility"),
                "price_action": features.get("price_action"),
            },
            data_quality=data_quality,
            trend=str(features.get("trend", "NEUTRAL")),
            momentum=str(features.get("momentum", "NEUTRAL")),
            volatility=str(features.get("volatility", "NEUTRAL")),
            rsi=features.get("rsi"),  # type: ignore[arg-type]
            ema_fast=features.get("ema_fast"),  # type: ignore[arg-type]
            ema_slow=features.get("ema_slow"),  # type: ignore[arg-type]
            price_action=str(features.get("price_action", "NEUTRAL")),
            overall_bias=overall_bias,
        )
