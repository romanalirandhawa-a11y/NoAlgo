from __future__ import annotations

from datetime import datetime

from src.data.models import AnalysisResult, Direction, Instrument, PaperResult, TradeResult
from src.market.live_service import LiveMarketDataService
from src.signals.models import PaperSignal, SignalOutcome


class TelegramFormatter:
    def format_analysis(self, result: AnalysisResult, instrument: Instrument, timeframe: str, timestamp: datetime | None) -> str:
        emoji = "🟢▲" if result.direction == Direction.BULLISH else "🔴▼" if result.direction == Direction.BEARISH else "⚪-"
        trend = result.trend or "NEUTRAL"
        momentum = result.momentum or "NEUTRAL"
        volatility = result.volatility or "NEUTRAL"
        rsi = result.rsi
        rsi_text = f"{rsi:.0f}" if rsi is not None else "N/A"
        confidence = f"{result.confidence:.0%}"
        time_str = timestamp.strftime("%H:%M") if timestamp else "N/A"
        return (
            "⚡=== 𝗠𝗔𝗥𝗞𝗘𝗧 𝗔𝗜 𝗟𝗜𝗩𝗘 ===⚡\n\n"
            f"📊 𝗠𝗮𝗿𝗸𝗲𝘁: {instrument}\n"
            f"🕐 𝗧𝗶𝗺𝗲: {time_str} (UTC)\n"
            f"⏳ 𝗧𝗙: {timeframe}\n\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"📶 𝗕𝗶𝗮𝘀: {result.direction} {emoji}\n"
            f"🎯 𝗣𝗿𝗶𝗰𝗲: {result.features.get('ema_fast', result.features.get('price', 'N/A'))}\n\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"🤖 𝗔𝗜 𝗔𝗡𝗔𝗟𝗬𝗦𝗜𝗦\n\n"
            f"📈 Trend: {trend}\n"
            f"⚡ Momentum: {momentum}\n"
            f"📊 RSI: {rsi_text}\n"
            f"〽️ Volatility: {volatility}\n\n"
            f"🎯 Confidence: {confidence}\n"
            f"Confidence here means feature agreement only.\n"
            f"It MUST NOT be described as probability of winning/profit.\n\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🚀 𝗠𝗔𝗥𝗞𝗘𝗧 𝗔𝗜 | 𝗟𝗜𝗩𝗘 𝗔𝗡𝗔𝗟𝗬𝗦𝗜𝗦\n"
        )

    def format_signal(self, signal: PaperSignal, latest_price: float) -> str:
        direction_emoji = "🟢▲" if signal.direction == "BULLISH" else "🔴▼" if signal.direction == "BEARISH" else "⚪-"
        confidence = f"{signal.confidence:.0%}"
        time_str = signal.timestamp.strftime("%H:%M UTC") if signal.timestamp else "N/A"
        expiry_text = f"{signal.expiry_periods} candle(s)" if signal.expiry_periods else "N/A"
        return (
            "⚡ ALPHAPULSE AI ⚡\n\n"
            f"📊 {signal.instrument}\n"
            f"⏱ {signal.timeframe}\n"
            f"🕐 {time_str}\n\n"
            f"{direction_emoji} {signal.direction}\n"
            f"🎯 Entry: {signal.entry_price:.5f}\n"
            f"📈 Confidence: {confidence}\n\n"
            f"📝 PAPER SIGNAL\n"
            f"⏳ Awaiting result...\n"
            f"⏱ Expiry: {expiry_text}\n"
        )

    def format_signal_result(self, signal: PaperSignal) -> str:
        direction_emoji = "🟢▲" if signal.direction == "BULLISH" else "🔴▼" if signal.direction == "BEARISH" else "⚪-"
        result_emoji = "✅" if signal.outcome == SignalOutcome.WIN else "❌" if signal.outcome == SignalOutcome.LOSS else "➖"
        exit_text = f"{signal.exit_price:.5f}" if signal.exit_price is not None else "N/A"
        return (
            "⚡ ALPHAPULSE AI ⚡\n\n"
            f"📊 {signal.instrument}\n"
            f"{direction_emoji} {signal.direction}\n\n"
            f"🎯 Entry: {signal.entry_price:.5f}\n"
            f"{result_emoji} Result: {signal.outcome.value}\n"
            f"📌 Exit: {exit_text}\n"
        )

    def format_result(self, result: PaperResult) -> str:
        emoji = "🟢" if result.result == TradeResult.CORRECT else "🔴"
        return (
            "✅ PAPER RESULT\n"
            "━━━━━━━━━━━━━━━━━\n"
            f"📊 Asset     : {result.instrument}\n"
            f"🎯 Bias      : {result.direction} {emoji}\n"
            f"📈 Result    : {result.result}\n"
            f"━━━━━━━━━━━━━━━━━"
        )

    def format_status(
        self,
        market_service: LiveMarketDataService,
        instrument: Instrument,
        timeframe: str,
    ) -> str:
        provider_name = "mock"
        if market_service.provider.__class__.__name__ == "AlphaVantageProvider":
            provider_name = "alpha_vantage"
        last_success = market_service.last_success
        last_error = market_service.last_error
        if last_success:
            status = "Ready"
            reason = ""
            last_update = last_success.strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            status = "OFFLINE"
            reason = last_error or "No data yet"
            last_update = "N/A"
        text = (
            "📡 MARKET DATA STATUS\n\n"
            f"Provider: {provider_name}\n"
            f"Instrument: {instrument}\n"
            f"Timeframe: {timeframe}\n"
            f"Service: {status}\n"
            f"Last Update: {last_update}\n"
        )
        if reason and status == "OFFLINE":
            text += f"Reason: {reason}\n"
        return text
