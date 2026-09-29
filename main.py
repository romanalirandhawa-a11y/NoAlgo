from __future__ import annotations

import logging

from src.analysis.engine import AnalysisEngine
from src.analysis.live_analysis import LiveAnalysisService
from src.charts.generator import ChartGenerator
from src.config.settings import Settings
from src.market.factory import create_market_service
from src.signals.ledger import SignalLedgerStore
from src.signals.scheduler import LiveSignalScheduler
from src.telegram.bot import TelegramBot
from src.telegram.formatter import TelegramFormatter


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        settings = Settings.from_env()
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 1

    market_service = create_market_service(
        name=settings.market_data_provider,
        api_key=settings.market_data_api_key,
        twelvedata_api_key=settings.twelvedata_api_key,
    )
    analysis_engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=analysis_engine)
    chart_generator = ChartGenerator(output_dir=settings.chart_output_dir)
    ledger = SignalLedgerStore(output_dir="data/paper_signals")
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=analysis_engine,
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
    bot.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
