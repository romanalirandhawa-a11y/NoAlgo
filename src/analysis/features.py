from __future__ import annotations

from collections.abc import Mapping

from src.analysis.enums import DataQuality, Momentum, PriceAction, Trend
from src.analysis.indicators import (
    atr,
    classify_momentum,
    classify_price_action,
    classify_rsi,
    classify_trend,
    classify_volatility,
    ema,
    rsi,
)
from src.analysis.indicators import (
    momentum as momentum_indicator,
)
from src.data.models import Candle


class AnalysisError(Exception):
    pass


def extract_features(candles: list[Candle], now_index: int) -> dict[str, float | str | None]:
    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]

    ema9_series = ema(closes, 9)
    ema21_series = ema(closes, 21)
    rsi_series = rsi(closes, 14)
    atr_series = atr(highs, lows, closes, 14)
    momentum_series = momentum_indicator(closes, 5)

    price = closes[now_index]
    ema9 = ema9_series[now_index]
    ema21 = ema21_series[now_index]
    rsi_val = rsi_series[now_index]
    atr_raw = atr_series[now_index]
    atr_val: float = atr_raw if atr_raw is not None else 0.0
    momentum_raw = momentum_series[now_index]
    momentum_val: float = momentum_raw if momentum_raw is not None else 0.0

    trend = classify_trend(price, ema9, ema21)
    momentum_cls = classify_momentum(momentum_val)
    volatility_cls = classify_volatility(atr_val, price)
    rsi_trend = classify_rsi(rsi_val)
    price_action_cls = classify_price_action(candles[: now_index + 1])

    return {
        "price": price,
        "ema_fast": ema9,
        "ema_slow": ema21,
        "rsi": rsi_val,
        "atr": atr_val,
        "momentum_value": momentum_val,
        "trend": trend,
        "momentum": momentum_cls,
        "volatility": volatility_cls,
        "rsi_trend": rsi_trend,
        "price_action": price_action_cls,
    }


def assess_data_quality(candles: list[Candle], required: int = 30) -> str:
    if len(candles) < required:
        return DataQuality.INSUFFICIENT
    if len(candles) < required + 5:
        return DataQuality.LIMITED
    return DataQuality.GOOD


def compute_overall_bias(features: Mapping[str, object]) -> str:
    votes: list[str] = []
    for key in ("trend", "momentum", "rsi_trend", "price_action"):
        value = features.get(key)
        if value in (Trend.BULLISH, Momentum.POSITIVE, PriceAction.BULLISH):
            votes.append("BULLISH")
        elif value in (Trend.BEARISH, Momentum.NEGATIVE, PriceAction.BEARISH):
            votes.append("BEARISH")
    if not votes:
        return "NEUTRAL"
    bullish = votes.count("BULLISH")
    bearish = votes.count("BEARISH")
    if bullish > bearish:
        return "BULLISH"
    if bearish > bullish:
        return "BEARISH"
    return "NEUTRAL"


def compute_confidence(features: Mapping[str, object]) -> float:
    votes: list[str] = []
    for key in ("trend", "momentum", "rsi_trend", "price_action"):
        value = features.get(key)
        if value in ("BULLISH", "BEARISH"):
            votes.append(value)
    if not votes:
        return 0.0
    overall_bias = compute_overall_bias(features)
    agreement = votes.count(overall_bias)
    return agreement / len(votes)
