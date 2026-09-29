from datetime import datetime, timezone

from src.data.models import AnalysisResult, Direction, Instrument, PaperResult, TradeResult
from src.signals.models import PaperSignal, SignalOutcome, SignalState
from src.telegram.formatter import TelegramFormatter


def test_format_analysis_bullish() -> None:
    fmt = TelegramFormatter()
    result = AnalysisResult(
        instrument=Instrument(symbol="EUR/USD"),
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        direction=Direction.BULLISH,
        confidence=0.8,
        reason="test",
        trend="BULLISH",
        momentum="POSITIVE",
        volatility="NORMAL",
        rsi=61.0,
        ema_fast=1.1732,
        ema_slow=1.1730,
        price_action="BULLISH",
        overall_bias="BULLISH",
    )
    text = fmt.format_analysis(result, Instrument(symbol="EUR/USD"), "M1", datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc))
    assert "EUR/USD" in text
    assert "BULLISH" in text
    assert "61" in text
    assert "feature agreement only" in text


def test_format_analysis_bearish() -> None:
    fmt = TelegramFormatter()
    result = AnalysisResult(
        instrument=Instrument(symbol="EUR/USD"),
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        direction=Direction.BEARISH,
        confidence=0.3,
        reason="test",
        trend="BEARISH",
        momentum="NEGATIVE",
        volatility="HIGH",
        rsi=39.0,
        ema_fast=1.1728,
        ema_slow=1.1732,
        price_action="BEARISH",
        overall_bias="BEARISH",
    )
    text = fmt.format_analysis(result, Instrument(symbol="EUR/USD"), "M1", datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc))
    assert "BEARISH" in text
    assert "39" in text
    assert "feature agreement only" in text


def test_format_analysis_neutral() -> None:
    fmt = TelegramFormatter()
    result = AnalysisResult(
        instrument=Instrument(symbol="EUR/USD"),
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        direction=Direction.NEUTRAL,
        confidence=0.0,
        reason="test",
        trend="NEUTRAL",
        momentum="NEUTRAL",
        volatility="NORMAL",
        rsi=50.0,
        ema_fast=1.1730,
        ema_slow=1.1730,
        price_action="NEUTRAL",
        overall_bias="NEUTRAL",
    )
    text = fmt.format_analysis(result, Instrument(symbol="EUR/USD"), "M1", datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc))
    assert "NEUTRAL" in text
    assert "feature agreement only" in text


def test_format_analysis_no_api_keys() -> None:
    fmt = TelegramFormatter()
    result = AnalysisResult(
        instrument=Instrument(symbol="EUR/USD"),
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        direction=Direction.BULLISH,
        confidence=0.8,
        reason="test",
    )
    text = fmt.format_analysis(result, Instrument(symbol="EUR/USD"), "M1", datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc))
    assert "TELEGRAM_BOT_TOKEN" not in text
    assert "MARKET_DATA_API_KEY" not in text


def test_format_result() -> None:
    fmt = TelegramFormatter()
    result = PaperResult(
        instrument=Instrument(symbol="EUR/USD"),
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        direction=Direction.BULLISH,
        result=TradeResult.CORRECT,
        entry_price=1.17300,
        exit_price=1.17350,
        profit=0.0005,
    )
    text = fmt.format_result(result)
    assert "PAPER RESULT" in text
    assert "CORRECT" in text


def test_format_signal_bullish() -> None:
    fmt = TelegramFormatter()
    signal = PaperSignal(
        id="sig1",
        instrument=Instrument(symbol="EUR/USD"),
        timeframe="M1",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        entry_price=1.17300,
        direction="BULLISH",
        confidence=0.82,
        state=SignalState.PENDING,
        outcome=SignalOutcome.PENDING,
        expiry_periods=1,
        expiry_timestamp=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
    )
    text = fmt.format_signal(signal, 1.17305)
    assert "EUR/USD" in text
    assert "M1" in text
    assert "BULLISH" in text
    assert "1.17300" in text
    assert "82%" in text
    assert "Awaiting result" in text
    assert "Expiry: 1 candle(s)" in text


def test_format_signal_bearish() -> None:
    fmt = TelegramFormatter()
    signal = PaperSignal(
        id="sig2",
        instrument=Instrument(symbol="GBP/USD"),
        timeframe="M1",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        entry_price=1.25000,
        direction="BEARISH",
        confidence=0.75,
        state=SignalState.PENDING,
        outcome=SignalOutcome.PENDING,
        expiry_periods=2,
        expiry_timestamp=datetime(2026, 1, 1, 12, 2, tzinfo=timezone.utc),
    )
    text = fmt.format_signal(signal, 1.24995)
    assert "GBP/USD" in text
    assert "BEARISH" in text
    assert "1.25000" in text
    assert "75%" in text
    assert "Expiry: 2 candle(s)" in text


def test_format_signal_result_win() -> None:
    fmt = TelegramFormatter()
    signal = PaperSignal(
        id="sig1",
        instrument=Instrument(symbol="EUR/USD"),
        timeframe="M1",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        entry_price=1.17300,
        direction="BULLISH",
        confidence=0.82,
        state=SignalState.RESOLVED,
        outcome=SignalOutcome.WIN,
        exit_price=1.17350,
    )
    text = fmt.format_signal_result(signal)
    assert "WIN" in text
    assert "1.17350" in text
    assert "✅" in text


def test_format_signal_result_loss() -> None:
    fmt = TelegramFormatter()
    signal = PaperSignal(
        id="sig1",
        instrument=Instrument(symbol="EUR/USD"),
        timeframe="M1",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        entry_price=1.17300,
        direction="BULLISH",
        confidence=0.82,
        state=SignalState.RESOLVED,
        outcome=SignalOutcome.LOSS,
        exit_price=1.17250,
    )
    text = fmt.format_signal_result(signal)
    assert "LOSS" in text
    assert "1.17250" in text
    assert "❌" in text


def test_format_signal_result_draw() -> None:
    fmt = TelegramFormatter()
    signal = PaperSignal(
        id="sig1",
        instrument=Instrument(symbol="EUR/USD"),
        timeframe="M1",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        entry_price=1.17300,
        direction="BULLISH",
        confidence=0.82,
        state=SignalState.RESOLVED,
        outcome=SignalOutcome.DRAW,
        exit_price=1.17300,
    )
    text = fmt.format_signal_result(signal)
    assert "DRAW" in text
    assert "➖" in text


def test_format_signal_result_pending() -> None:
    fmt = TelegramFormatter()
    signal = PaperSignal(
        id="sig1",
        instrument=Instrument(symbol="EUR/USD"),
        timeframe="M1",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        entry_price=1.17300,
        direction="BULLISH",
        confidence=0.82,
        state=SignalState.PENDING,
        outcome=SignalOutcome.PENDING,
    )
    text = fmt.format_signal_result(signal)
    assert "PENDING" in text
    assert "N/A" in text


def test_format_signal_uses_actual_signal_data() -> None:
    fmt = TelegramFormatter()
    signal = PaperSignal(
        id="sig_check",
        instrument=Instrument(symbol="USD/JPY"),
        timeframe="M1",
        timestamp=datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc),
        entry_price=150.250,
        direction="BEARISH",
        confidence=0.91,
        state=SignalState.PENDING,
        outcome=SignalOutcome.PENDING,
        expiry_periods=1,
        expiry_timestamp=datetime(2026, 1, 1, 12, 31, tzinfo=timezone.utc),
    )
    text = fmt.format_signal(signal, 150.245)
    assert "USD/JPY" in text
    assert "BEARISH" in text
    assert "150.25000" in text
    assert "91%" in text
    assert "12:30 UTC" in text


def test_format_signal_no_secret_leakage() -> None:
    fmt = TelegramFormatter()
    signal = PaperSignal(
        id="sig1",
        instrument=Instrument(symbol="EUR/USD"),
        timeframe="M1",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        entry_price=1.17300,
        direction="BULLISH",
        confidence=0.82,
        state=SignalState.PENDING,
        outcome=SignalOutcome.PENDING,
    )
    text = fmt.format_signal(signal, 1.17305)
    result_text = fmt.format_signal_result(signal)
    assert "TELEGRAM_BOT_TOKEN" not in text
    assert "MARKET_DATA_API_KEY" not in text
    assert "TWELVEDATA_API_KEY" not in text
    assert "TELEGRAM_BOT_TOKEN" not in result_text
    assert "MARKET_DATA_API_KEY" not in result_text
    assert "TWELVEDATA_API_KEY" not in result_text


def test_format_analysis_timestamp_uses_actual_timestamp() -> None:
    fmt = TelegramFormatter()
    ts = datetime(2026, 1, 1, 15, 45, tzinfo=timezone.utc)
    result = AnalysisResult(
        instrument=Instrument(symbol="EUR/USD"),
        timestamp=ts,
        direction=Direction.BULLISH,
        confidence=0.8,
        reason="test",
    )
    text = fmt.format_analysis(result, Instrument(symbol="EUR/USD"), "M1", ts)
    assert "15:45" in text
