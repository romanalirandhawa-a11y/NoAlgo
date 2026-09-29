from __future__ import annotations

import sys
from unittest.mock import MagicMock

# The project contains a local package named `src/telegram`, which shadows
# the installed `python-telegram-bot` package when pytest adds `src` to sys.path.
# We pre-populate sys.modules with mocks so that importing src.telegram.bot
# does not fail on `from telegram.ext import ...`.
_telegram_mock = MagicMock()
_telegram_ext_mock = MagicMock()
_telegram_request_mock = MagicMock()
_telegram_error_mock = MagicMock()
_telegram_mock.ext = _telegram_ext_mock
_telegram_mock.error = _telegram_error_mock
_telegram_mock.request = _telegram_request_mock
sys.modules.setdefault("telegram", _telegram_mock)
sys.modules.setdefault("telegram.ext", _telegram_ext_mock)
sys.modules.setdefault("telegram.request", _telegram_request_mock)
sys.modules.setdefault("telegram.error", _telegram_error_mock)

import os
from unittest.mock import MagicMock, patch

import pytest

from src.config.settings import Settings
from src.signals.scheduler import LiveSignalScheduler
from src.telegram.formatter import TelegramFormatter


def test_telegram_application_can_be_constructed() -> None:
    with patch.dict(sys.modules, {"telegram.ext": MagicMock()}):
        from src.telegram.bot import TelegramBot

        settings = Settings(
            telegram_bot_token="test-token",
            market_data_provider="mock",
            market_data_api_key="",
        )
        from src.analysis.engine import AnalysisEngine
        from src.analysis.live_analysis import LiveAnalysisService
        from src.charts.generator import ChartGenerator
        from src.market.factory import create_market_service
        from src.market.mock_provider import MockMarketDataProvider
        from src.signals.ledger import SignalLedgerStore

        MockMarketDataProvider()
        market_service = create_market_service(name="mock", api_key="")
        live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=AnalysisEngine())
        chart_generator = ChartGenerator(output_dir="data/charts")
        ledger = SignalLedgerStore(output_dir="data/paper_signals")
        scheduler = LiveSignalScheduler(
            market_service=market_service,
            analysis_engine=AnalysisEngine(),
            live_analysis=live_analysis,
            chart_generator=chart_generator,
            ledger=ledger,
            formatter=TelegramFormatter(),
            send_callback=lambda text: None,
            instruments=None,
            interval_seconds=60,
            expiry_periods=1,
            confidence_threshold=0.7,
            enabled=False,
        )
        bot = TelegramBot(settings=settings, live_analysis=live_analysis, scheduler=scheduler)
        assert bot.application is not None
        assert bot.scheduler.is_running() is False


def test_handlers_are_registered() -> None:
    with patch.dict(sys.modules, {"telegram.ext": MagicMock()}):
        from src.telegram.bot import TelegramBot

        settings = Settings(
            telegram_bot_token="test-token",
            market_data_provider="mock",
            market_data_api_key="",
        )
        from src.analysis.engine import AnalysisEngine
        from src.analysis.live_analysis import LiveAnalysisService
        from src.charts.generator import ChartGenerator
        from src.market.factory import create_market_service
        from src.market.mock_provider import MockMarketDataProvider
        from src.signals.ledger import SignalLedgerStore

        MockMarketDataProvider()
        market_service = create_market_service(name="mock", api_key="")
        live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=AnalysisEngine())
        chart_generator = ChartGenerator(output_dir="data/charts")
        ledger = SignalLedgerStore(output_dir="data/paper_signals")
        scheduler = LiveSignalScheduler(
            market_service=market_service,
            analysis_engine=AnalysisEngine(),
            live_analysis=live_analysis,
            chart_generator=chart_generator,
            ledger=ledger,
            formatter=TelegramFormatter(),
            send_callback=lambda text: None,
            instruments=None,
            interval_seconds=60,
            expiry_periods=1,
            confidence_threshold=0.7,
            enabled=False,
        )
        bot = TelegramBot(settings=settings, live_analysis=live_analysis, scheduler=scheduler)
        assert bot.application.add_handler.call_count == 7  # type: ignore[attr-defined]
        handler_calls = [call.args[0] for call in bot.application.add_handler.call_args_list]  # type: ignore[attr-defined]
        assert all("CommandHandler" in repr(h) for h in handler_calls)


def test_scheduler_is_disabled_by_default() -> None:
    from src.analysis.engine import AnalysisEngine
    from src.analysis.live_analysis import LiveAnalysisService
    from src.charts.generator import ChartGenerator
    from src.market.factory import create_market_service
    from src.market.mock_provider import MockMarketDataProvider
    from src.signals.ledger import SignalLedgerStore

    settings = Settings(
        telegram_bot_token="test-token",
        market_data_provider="mock",
        market_data_api_key="",
    )
    MockMarketDataProvider()
    market_service = create_market_service(name="mock", api_key="")
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=AnalysisEngine())
    chart_generator = ChartGenerator(output_dir="data/charts")
    ledger = SignalLedgerStore(output_dir="data/paper_signals")
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=AnalysisEngine(),
        live_analysis=live_analysis,
        chart_generator=chart_generator,
        ledger=ledger,
        formatter=TelegramFormatter(),
        send_callback=lambda text: None,
        instruments=None,
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.7,
        enabled=False,
    )
    with patch.dict(sys.modules, {"telegram.ext": MagicMock()}):
        from src.telegram.bot import TelegramBot

        bot = TelegramBot(settings=settings, live_analysis=live_analysis, scheduler=scheduler)
    assert bot.scheduler.is_running() is False


def test_missing_telegram_token_raises_clear_error() -> None:
    with patch.dict(os.environ, {}, clear=True), patch("src.config.settings.load_dotenv"):
        with pytest.raises(ValueError) as exc_info:
            Settings.from_env()
        assert "TELEGRAM_BOT_TOKEN" in str(exc_info.value)


def test_missing_market_data_key_does_not_crash_startup_with_mock() -> None:
    with patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test-token",
        "MARKET_DATA_PROVIDER": "mock",
    }, clear=True), patch("src.config.settings.load_dotenv"):
        settings = Settings.from_env()
        assert settings.market_data_provider == "mock"
        assert settings.market_data_api_key == ""


def test_formatter_imports_work() -> None:
    fmt = TelegramFormatter()
    assert fmt is not None


def test_main_wiring_does_not_raise_name_error() -> None:
    from src.analysis.engine import AnalysisEngine
    from src.analysis.live_analysis import LiveAnalysisService
    from src.charts.generator import ChartGenerator
    from src.market.factory import create_market_service
    from src.market.mock_provider import MockMarketDataProvider
    from src.signals.ledger import SignalLedgerStore
    from src.signals.scheduler import LiveSignalScheduler

    settings = Settings(
        telegram_bot_token="test-token",
        market_data_provider="mock",
        market_data_api_key="",
    )
    MockMarketDataProvider()
    market_service = create_market_service(name="mock", api_key="")
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=AnalysisEngine())
    chart_generator = ChartGenerator(output_dir="data/charts")
    ledger = SignalLedgerStore(output_dir="data/paper_signals")
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=AnalysisEngine(),
        live_analysis=live_analysis,
        chart_generator=chart_generator,
        ledger=ledger,
        formatter=TelegramFormatter(),
        send_callback=lambda text: None,
        instruments=None,
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.7,
        enabled=False,
    )
    with patch.dict(sys.modules, {"telegram.ext": MagicMock()}):
        from src.telegram.bot import TelegramBot

        bot = TelegramBot(settings=settings, live_analysis=live_analysis, scheduler=scheduler)
    assert bot is not None


def test_no_duplicate_scheduler_task() -> None:
    from src.analysis.engine import AnalysisEngine
    from src.analysis.live_analysis import LiveAnalysisService
    from src.charts.generator import ChartGenerator
    from src.market.factory import create_market_service
    from src.market.mock_provider import MockMarketDataProvider
    from src.signals.ledger import SignalLedgerStore

    settings = Settings(
        telegram_bot_token="test-token",
        market_data_provider="mock",
        market_data_api_key="",
    )
    MockMarketDataProvider()
    market_service = create_market_service(name="mock", api_key="")
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=AnalysisEngine())
    chart_generator = ChartGenerator(output_dir="data/charts")
    ledger = SignalLedgerStore(output_dir="data/paper_signals")
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=AnalysisEngine(),
        live_analysis=live_analysis,
        chart_generator=chart_generator,
        ledger=ledger,
        formatter=TelegramFormatter(),
        send_callback=lambda text: None,
        instruments=None,
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.7,
        enabled=False,
    )
    with patch.dict(sys.modules, {"telegram.ext": MagicMock()}):
        from src.telegram.bot import TelegramBot

        TelegramBot(settings=settings, live_analysis=live_analysis, scheduler=scheduler)
    scheduler.start()
    first_task = scheduler._task
    scheduler.start()
    second_task = scheduler._task
    assert first_task is second_task
    scheduler.stop()
