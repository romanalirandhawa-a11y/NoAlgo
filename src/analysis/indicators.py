from __future__ import annotations

import math
from dataclasses import dataclass

from src.analysis.enums import Momentum, PriceAction, Trend, Volatility
from src.data.models import Candle


@dataclass(frozen=True)
class FeatureVector:
    trend: str = Trend.NEUTRAL
    momentum: str = Momentum.NEUTRAL
    volatility: str = Volatility.NORMAL
    rsi: float | None = None
    ema_fast: float | None = None
    ema_slow: float | None = None
    price_action: str = PriceAction.NEUTRAL
    momentum_value: float = 0.0
    atr: float = 0.0
    bullish_candle_ratio: float = 0.0
    higher_highs: bool = False
    lower_lows: bool = False


def ema(values: list[float], period: int) -> list[float | None]:
    if len(values) < period or period <= 0:
        return [None] * len(values)
    k = 2 / (period + 1)
    result: list[float | None] = [None] * len(values)
    sma = sum(values[:period]) / period
    result[period - 1] = sma
    prev = sma
    for i in range(period, len(values)):
        value = values[i] * k + prev * (1 - k)
        result[i] = value
        prev = value
    return result


def rsi(closes: list[float], period: int = 14) -> list[float | None]:
    if len(closes) <= period or period <= 0:
        return [None] * len(closes)
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(0.0, delta))
        losses.append(max(0.0, -delta))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result: list[float | None] = [None] * len(closes)
    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100 - 100 / (1 + rs)
    for i in range(period, len(gains)):
        gain = gains[i]
        loss = losses[i]
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            result[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100 - 100 / (1 + rs)
    return result


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float | None]:
    if len(closes) <= period or period <= 0:
        return [None] * len(closes)
    trs: list[float] = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    result: list[float | None] = [None] * len(closes)
    atr_val = sum(trs[:period]) / period
    result[period] = atr_val
    for i in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
        result[i + 1] = atr_val
    return result


def momentum(closes: list[float], period: int = 5) -> list[float | None]:
    if len(closes) <= period or period <= 0:
        return [None] * len(closes)
    return [None] * period + [closes[i] - closes[i - period] for i in range(period, len(closes))]


def classify_trend(price: float, ema_fast: float | None, ema_slow: float | None) -> str:
    if ema_fast is None or ema_slow is None:
        return Trend.NEUTRAL
    if price > ema_fast > ema_slow:
        return Trend.BULLISH
    if price < ema_fast < ema_slow:
        return Trend.BEARISH
    return Trend.NEUTRAL


def classify_momentum(momentum_value: float) -> str:
    if momentum_value > 0:
        return Momentum.POSITIVE
    if momentum_value < 0:
        return Momentum.NEGATIVE
    return Momentum.NEUTRAL


def classify_volatility(atr_value: float, price: float) -> str:
    if price <= 0:
        return Volatility.NORMAL
    ratio = atr_value / price
    if ratio > 0.001:
        return Volatility.HIGH
    if ratio < 0.0003:
        return Volatility.LOW
    return Volatility.NORMAL


def classify_rsi(rsi_value: float | None) -> str:
    if rsi_value is None or math.isnan(rsi_value):
        return Trend.NEUTRAL
    if rsi_value > 55:
        return Trend.BULLISH
    if rsi_value < 45:
        return Trend.BEARISH
    return Trend.NEUTRAL


def classify_price_action(candles: list[Candle], lookback: int = 5) -> str:
    if len(candles) < lookback:
        return PriceAction.NEUTRAL
    recent = candles[-lookback:]
    highs = [c.high for c in recent]
    lows = [c.low for c in recent]
    closes = [c.close for c in recent]
    opens = [c.open for c in recent]
    bullish = sum(1 for open_, close_ in zip(opens, closes) if close_ > open_)
    bullish_ratio = bullish / lookback
    higher_highs = all(highs[i] >= highs[i - 1] for i in range(1, len(highs)))
    lower_lows = all(lows[i] <= lows[i - 1] for i in range(1, len(lows)))
    if higher_highs and bullish_ratio >= 0.6:
        return PriceAction.BULLISH
    if lower_lows and bullish_ratio <= 0.4:
        return PriceAction.BEARISH
    return PriceAction.NEUTRAL
