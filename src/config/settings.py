from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    telegram_bot_token: str
    market_data_api_key: str = ""
    market_data_provider: str = "mock"
    twelvedata_api_key: str = ""
    default_instrument: str = "EUR/USD"
    default_timeframe: str = "M1"
    chart_output_dir: str = "charts"
    historical_data_dir: str = "data/historical"
    backtest_output_dir: str = "data/backtests"
    live_signal_enabled: bool = False
    live_signal_interval_seconds: int = 60
    live_signal_instruments: str = "EUR/USD,GBP/USD,USD/JPY,AUD/USD"
    live_signal_expiry_periods: int = 1
    live_signal_confidence_threshold: float = 0.7

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        provider = os.getenv("MARKET_DATA_PROVIDER", "mock")
        api_key = os.getenv("MARKET_DATA_API_KEY", "")
        twelvedata_api_key = os.getenv("TWELVEDATA_API_KEY", "")
        if provider == "alpha_vantage" and not api_key:
            raise ValueError("MARKET_DATA_API_KEY is required when MARKET_DATA_PROVIDER is alpha_vantage")
        if provider == "twelvedata" and not twelvedata_api_key:
            raise ValueError("TWELVEDATA_API_KEY is required when MARKET_DATA_PROVIDER is twelvedata")
        live_signal_instruments = os.getenv("LIVE_SIGNAL_INSTRUMENTS", "EUR/USD,GBP/USD,USD/JPY,AUD/USD")
        instruments = [s.strip() for s in live_signal_instruments.split(",") if s.strip()]
        return cls(
            telegram_bot_token=token,
            market_data_api_key=api_key,
            market_data_provider=provider,
            twelvedata_api_key=twelvedata_api_key,
            default_instrument=os.getenv("DEFAULT_INSTRUMENT", "EUR/USD"),
            default_timeframe=os.getenv("DEFAULT_TIMEFRAME", "M1"),
            chart_output_dir=os.getenv("CHART_OUTPUT_DIR", "charts"),
            historical_data_dir=os.getenv("HISTORICAL_DATA_DIR", "data/historical"),
            backtest_output_dir=os.getenv("BACKTEST_OUTPUT_DIR", "data/backtests"),
            live_signal_enabled=os.getenv("LIVE_SIGNAL_ENABLED", "false").lower() == "true",
            live_signal_interval_seconds=int(os.getenv("LIVE_SIGNAL_INTERVAL_SECONDS", "60")),
            live_signal_instruments=",".join(instruments),
            live_signal_expiry_periods=int(os.getenv("LIVE_SIGNAL_EXPIRY_PERIODS", "1")),
            live_signal_confidence_threshold=float(os.getenv("LIVE_SIGNAL_CONFIDENCE_THRESHOLD", "0.7")),
        )
