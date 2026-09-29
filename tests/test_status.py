from datetime import datetime, timezone

from src.data.models import Instrument
from src.market.live_service import LiveMarketDataService
from src.telegram.formatter import TelegramFormatter


def test_status_format() -> None:
    from src.market.mock_provider import MockMarketDataProvider

    provider = MockMarketDataProvider()
    service = LiveMarketDataService(provider=provider)
    service.last_success = datetime.now(timezone.utc)
    fmt = TelegramFormatter()
    text = fmt.format_status(service, Instrument(symbol="EUR/USD"), "M1")
    assert "Ready" in text
    assert "EUR/USD" in text
    assert "M1" in text


def test_status_format_offline() -> None:
    from src.market.mock_provider import MockMarketDataProvider

    provider = MockMarketDataProvider()
    service = LiveMarketDataService(provider=provider)
    service.last_error = "Network error"
    fmt = TelegramFormatter()
    text = fmt.format_status(service, Instrument(symbol="EUR/USD"), "M1")
    assert "OFFLINE" in text
    assert "Network error" in text
