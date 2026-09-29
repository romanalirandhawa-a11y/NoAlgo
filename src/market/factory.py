from __future__ import annotations

from src.market.alpha_vantage_provider import AlphaVantageProvider
from src.market.live_service import LiveMarketDataService
from src.market.mock_provider import MockMarketDataProvider
from src.market.provider import MarketDataProvider
from src.market.twelve_data_provider import TwelveDataProvider


def create_provider(name: str, api_key: str = "", twelvedata_api_key: str = "") -> MarketDataProvider:
    name = name.lower()
    if name == "mock":
        return MockMarketDataProvider()
    if name == "alpha_vantage":
        if not api_key:
            raise ValueError("Alpha Vantage provider requires MARKET_DATA_API_KEY")
        return AlphaVantageProvider(api_key=api_key)
    if name == "twelvedata":
        if not twelvedata_api_key:
            raise ValueError("Twelve Data provider requires TWELVEDATA_API_KEY")
        return TwelveDataProvider(api_key=twelvedata_api_key)
    raise ValueError(f"Unsupported market data provider: {name}")


def create_market_service(name: str, api_key: str = "", twelvedata_api_key: str = "") -> LiveMarketDataService:
    provider = create_provider(name=name, api_key=api_key, twelvedata_api_key=twelvedata_api_key)
    return LiveMarketDataService(provider=provider)
