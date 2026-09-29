from __future__ import annotations

import asyncio
import logging

from telegram.error import NetworkError, TimedOut
from telegram.ext import Application, CallbackContext, CommandHandler
from telegram.request import BaseRequest, HTTPXRequest

from src.analysis.live_analysis import LiveAnalysisService
from src.config.constants import SUPPORTED_INSTRUMENTS
from src.config.settings import Settings
from src.signals.scheduler import LiveSignalScheduler
from src.telegram.formatter import TelegramFormatter
from telegram import Update

logger = logging.getLogger(__name__)


def _build_request(connection_pool_size: int = 10) -> BaseRequest:
    return HTTPXRequest(
        connection_pool_size=connection_pool_size,
        read_timeout=15.0,
        write_timeout=15.0,
        connect_timeout=10.0,
        pool_timeout=5.0,
        media_write_timeout=20.0,
        http_version="1.1",
    )


class TelegramBot:
    def __init__(self, settings: Settings, live_analysis: LiveAnalysisService, scheduler: LiveSignalScheduler) -> None:
        self.settings = settings
        self.live_analysis = live_analysis
        self.scheduler = scheduler
        self.formatter = TelegramFormatter()
        request = _build_request()
        get_updates_request = _build_request()
        self.application = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .request(request)
            .get_updates_request(get_updates_request)
            .build()
        )
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(CommandHandler("analyze", self.analyze))
        self.application.add_handler(CommandHandler("startlive", self.startlive))
        self.application.add_handler(CommandHandler("stoplive", self.stoplive))
        self.application.add_handler(CommandHandler("live", self.live_status))
        self.application.add_error_handler(self._on_error)

    async def _on_error(self, update: object, context: CallbackContext) -> None:  # type: ignore[type-arg]
        logger.error("Telegram handler error: %s", context.error, exc_info=context.error)

    async def _safe_reply(self, update: Update, text: str, max_retries: int = 2) -> None:
        if not update.message:
            return
        chat = update.effective_chat
        for attempt in range(1, max_retries + 1):
            try:
                await update.message.reply_text(text)
                logger.info(
                    "Telegram reply sent | chat_type=%s | attempt=%s",
                    chat.type if chat else "None",
                    attempt,
                )
                return
            except (NetworkError, TimedOut) as exc:
                logger.warning(
                    "Telegram send attempt %s/%s failed: %s | chat_type=%s",
                    attempt,
                    max_retries,
                    type(exc).__name__,
                    chat.type if chat else "None",
                )
                if attempt == max_retries:
                    raise
                await asyncio.sleep(min(1 * attempt, 3))

    async def start(self, update: Update, context: CallbackContext) -> None:  # type: ignore[type-arg]
        chat = update.effective_chat
        logger.info("Telegram /start received | chat_type=%s", chat.type if chat else "None")
        if not update.message:
            return
        await self._safe_reply(
            update,
            "Welcome to the Market AI research bot. Use /help for available commands.",
        )

    async def help(self, update: Update, context: CallbackContext) -> None:  # type: ignore[type-arg]
        chat = update.effective_chat
        logger.info("Telegram /help received | chat_type=%s", chat.type if chat else "None")
        if not update.message:
            return
        await self._safe_reply(
            update,
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/status - Show bot and data feed status\n"
            "/analyze [instrument] - Run live market analysis\n"
            "/startlive - Start live paper signal scheduler\n"
            "/stoplive - Stop live paper signal scheduler\n"
            "/live - Show live scheduler status",
        )

    async def status(self, update: Update, context: CallbackContext) -> None:  # type: ignore[type-arg]
        chat = update.effective_chat
        logger.info("Telegram /status received | chat_type=%s", chat.type if chat else "None")
        if not update.message:
            return
        provider_name = self.settings.market_data_provider
        instrument = self.settings.default_instrument
        timeframe = self.settings.default_timeframe
        last_success = self.live_analysis.market_service.last_success
        last_error = self.live_analysis.market_service.last_error
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
        await self._safe_reply(update, text)

    async def analyze(self, update: Update, context: CallbackContext) -> None:  # type: ignore[type-arg]
        chat = update.effective_chat
        logger.info("Telegram /analyze received | chat_type=%s", chat.type if chat else "None")
        if not update.message:
            return
        try:
            instrument_symbol = self.settings.default_instrument
            if context.args:
                instrument_symbol = context.args[0].strip().upper()
            if instrument_symbol not in SUPPORTED_INSTRUMENTS:
                await self._safe_reply(
                    update,
                    f"Unsupported instrument: {instrument_symbol}\n"
                    f"Supported instruments: {', '.join(SUPPORTED_INSTRUMENTS)}",
                )
                return

            from src.data.models import Instrument

            instrument = Instrument(symbol=instrument_symbol)
            result = await self.live_analysis.analyze(
                instrument=instrument,
                timeframe=self.settings.default_timeframe,
                count=30,
            )
            text = self.formatter.format_analysis(result.analysis, instrument, result.timeframe, result.timestamp)
            await self._safe_reply(update, text)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Analysis command failed: %s", exc)
            await self._safe_reply(
                update,
                "⚠️ Live market data is currently unavailable.\n\n"
                "Please try again shortly.",
            )

    async def startlive(self, update: Update, context: CallbackContext) -> None:  # type: ignore[type-arg]
        chat = update.effective_chat
        logger.info("Telegram /startlive received | chat_type=%s", chat.type if chat else "None")
        if not update.message:
            return
        if self.scheduler.is_running():
            await self._safe_reply(update, "Live signal scheduler is already running.")
            return
        self.scheduler.enabled = True
        self.scheduler.start()
        await self._safe_reply(update, "Live paper signal scheduler started.")

    async def stoplive(self, update: Update, context: CallbackContext) -> None:  # type: ignore[type-arg]
        chat = update.effective_chat
        logger.info("Telegram /stoplive received | chat_type=%s", chat.type if chat else "None")
        if not update.message:
            return
        if not self.scheduler.is_running():
            await self._safe_reply(update, "Live signal scheduler is not running.")
            return
        self.scheduler.stop()
        await self._safe_reply(update, "Live paper signal scheduler stopped.")

    async def live_status(self, update: Update, context: CallbackContext) -> None:  # type: ignore[type-arg]
        chat = update.effective_chat
        logger.info("Telegram /live received | chat_type=%s", chat.type if chat else "None")
        if not update.message:
            return
        status = self.scheduler.status()
        candle_lines = [f"  {k}: {v}" for k, v in status.get("last_candle_ts", {}).items()]
        lines = [
            "📡 LIVE SIGNAL STATUS\n",
            f"Enabled: {status['enabled']}",
            f"Running: {status['running']}",
            f"Instruments: {', '.join(status['instruments'])}",
            f"Interval: {status['interval_seconds']}s",
            f"Expiry: {status['expiry_periods']} candle",
            f"Threshold: {status['confidence_threshold']:.0%}",
            f"Pending: {status['pending_signals']}",
            f"Last Activity: {status['last_activity'] or 'N/A'}",
        ]
        if candle_lines:
            lines.append("Latest Processed Candle:")
            lines.extend(candle_lines)
        await self._safe_reply(update, "\n".join(lines))

    def run(self) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        self.application.run_polling()
