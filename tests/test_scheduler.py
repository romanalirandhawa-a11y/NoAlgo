from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.analysis.engine import AnalysisEngine
from src.analysis.live_analysis import LiveAnalysisResult, LiveAnalysisService
from src.charts.generator import ChartGenerator
from src.data.models import Candle, Instrument
from src.market.live_service import LiveMarketDataService
from src.market.mock_provider import MockMarketDataProvider
from src.signals.ledger import SignalLedgerStore
from src.signals.models import PaperSignal, SignalOutcome, SignalState
from src.signals.scheduler import LiveSignalScheduler
from src.telegram.formatter import TelegramFormatter


def _instrument(symbol: str = "EUR/USD") -> Instrument:
    return Instrument(symbol=symbol)


def _candle(ts: datetime, close: float) -> Candle:
    return Candle(
        instrument=_instrument(),
        timestamp=ts,
        timeframe="M1",
        open=close - 0.0005,
        high=close + 0.0005,
        low=close - 0.0005,
        close=close,
    )


def _live_analysis_result(candles: list[Candle], direction: str = "BULLISH", confidence: float = 0.8) -> LiveAnalysisResult:
    from src.data.models import AnalysisResult

    analysis = AnalysisResult(
        instrument=_instrument(),
        timestamp=candles[-1].timestamp,
        direction=direction,
        confidence=confidence,
        reason="test",
        trend="BULLISH",
        momentum="POSITIVE",
        volatility="NORMAL",
        rsi=60.0,
        ema_fast=1.0,
        ema_slow=0.999,
        price_action="BULLISH",
        overall_bias="BULLISH",
    )
    return LiveAnalysisResult(
        instrument=_instrument(),
        timeframe="M1",
        timestamp=candles[-1].timestamp,
        latest_price=candles[-1].close,
        analysis=analysis,
        candles=candles,
    )


def test_new_candle_generates_signal(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    formatter.format_signal.return_value = "signal text"
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]

    with patch.object(live_analysis, "analyze", AsyncMock(return_value=_live_analysis_result(candles))):
        asyncio.run(scheduler._process_instrument("EUR/USD"))

    pending = ledger.pending()
    assert len(pending) == 1
    assert pending[0].state == SignalState.PENDING
    assert pending[0].direction == "BULLISH"


def test_same_candle_does_not_duplicate(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    formatter.format_signal.return_value = "signal text"
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]

    with patch.object(live_analysis, "analyze", AsyncMock(return_value=_live_analysis_result(candles))):
        asyncio.run(scheduler._process_instrument("EUR/USD"))
        asyncio.run(scheduler._process_instrument("EUR/USD"))

    pending = ledger.pending()
    assert len(pending) == 1


def test_neutral_analysis_is_skipped(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = [_candle(base.replace(minute=i), 1.0) for i in range(40)]

    result = _live_analysis_result(candles, direction="NEUTRAL", confidence=0.5)
    with patch.object(live_analysis, "analyze", AsyncMock(return_value=result)):
        asyncio.run(scheduler._process_instrument("EUR/USD"))

    assert len(ledger.all()) == 0


def test_low_confidence_is_skipped(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.9,
        enabled=True,
    )

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]
    result = _live_analysis_result(candles, direction="BULLISH", confidence=0.5)

    with patch.object(live_analysis, "analyze", AsyncMock(return_value=result)):
        asyncio.run(scheduler._process_instrument("EUR/USD"))

    assert len(ledger.all()) == 0


def test_insufficient_data_quality_is_skipped(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(10)]
    result = _live_analysis_result(candles, direction="BULLISH", confidence=1.0)
    result.analysis.data_quality = "INSUFFICIENT"

    with patch.object(live_analysis, "analyze", AsyncMock(return_value=result)):
        asyncio.run(scheduler._process_instrument("EUR/USD"))

    assert len(ledger.all()) == 0


def test_resolve_pending_signal_win(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    signal_candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]
    signal_result = _live_analysis_result(signal_candles, direction="BULLISH", confidence=1.0)

    expiry_candle = _candle(base.replace(minute=40), 1.0 + 40 * 0.001 + 0.0005)
    expiry_candles = signal_candles + [expiry_candle]
    expiry_result = _live_analysis_result(expiry_candles, direction="BULLISH", confidence=1.0)

    with patch.object(live_analysis, "analyze", AsyncMock(side_effect=[signal_result, expiry_result])):
        asyncio.run(scheduler._process_instrument("EUR/USD"))
        asyncio.run(scheduler._resolve_pending_signals(Instrument(symbol="EUR/USD")))

    pending = ledger.pending()
    assert len(pending) == 0
    resolved = [s for s in ledger.all() if s.state == SignalState.RESOLVED]
    assert len(resolved) == 1
    assert resolved[0].outcome == SignalOutcome.WIN
    assert resolved[0].exit_price == expiry_candle.close
    assert resolved[0].entry_price == signal_candles[-1].close


def test_resolve_pending_signal_pending_when_future_unavailable(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    signal_candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]
    signal_result = _live_analysis_result(signal_candles, direction="BULLISH", confidence=1.0)

    with patch.object(live_analysis, "analyze", AsyncMock(return_value=signal_result)):
        asyncio.run(scheduler._process_instrument("EUR/USD"))
        asyncio.run(scheduler._resolve_pending_signals(Instrument(symbol="EUR/USD")))

    pending = ledger.pending()
    assert len(pending) == 1
    assert pending[0].state == SignalState.PENDING
    assert pending[0].outcome == SignalOutcome.PENDING


def test_scheduler_start_stop(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=1,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    scheduler.start()
    assert scheduler.is_running() is True
    scheduler.stop()
    assert scheduler.is_running() is False


def test_repeated_start_does_not_create_duplicate_task(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    scheduler.start()
    first_task = scheduler._task
    scheduler.start()
    assert scheduler._task is first_task
    scheduler.stop()


def test_stop_without_start_is_safe(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    assert scheduler.is_running() is False
    scheduler.stop()
    assert scheduler.is_running() is False


def test_disabled_scheduler_remains_inactive(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=False,
    )

    assert scheduler.is_running() is False
    scheduler.start()
    assert scheduler.is_running() is False
    assert scheduler._task is None


def test_multiple_instruments_tracked_independently(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    formatter.format_signal.return_value = "signal text"
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD", "GBP/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    eur_base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    eur_candles = [_candle(eur_base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]
    eur_result = _live_analysis_result(eur_candles, direction="BULLISH", confidence=1.0)

    gbp_base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    gbp_candles = [_candle(gbp_base.replace(minute=i), 1.5 + i * 0.002) for i in range(40)]
    gbp_result = _live_analysis_result(gbp_candles, direction="BEARISH", confidence=1.0)

    call_count = 0

    async def fake_analyze(instrument: Instrument, timeframe: str, count: int) -> LiveAnalysisResult:
        nonlocal call_count
        call_count += 1
        if instrument.symbol == "EUR/USD":
            return eur_result
        return gbp_result

    with patch.object(live_analysis, "analyze", fake_analyze):
        asyncio.run(scheduler._process_instrument("EUR/USD"))
        asyncio.run(scheduler._process_instrument("GBP/USD"))

    assert len(ledger.pending()) == 2
    assert scheduler._last_candle_ts["EUR/USD"] == eur_candles[-1].timestamp
    assert scheduler._last_candle_ts["GBP/USD"] == gbp_candles[-1].timestamp


def test_new_candle_updates_last_timestamp(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    formatter.format_signal.return_value = "signal text"
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    first_candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]
    first_result = _live_analysis_result(first_candles, direction="BULLISH", confidence=1.0)

    second_candles = first_candles + [_candle(base.replace(minute=40), 1.0 + 40 * 0.001 + 0.0005)]
    second_result = _live_analysis_result(second_candles, direction="BEARISH", confidence=1.0)

    call_count = 0

    async def fake_analyze(instrument: Instrument, timeframe: str, count: int) -> LiveAnalysisResult:
        nonlocal call_count
        call_count += 1
        if call_count in (1, 2):
            return first_result
        return second_result

    with patch.object(live_analysis, "analyze", fake_analyze):
        asyncio.run(scheduler._process_instrument("EUR/USD"))
        assert len(ledger.pending()) == 1
        assert scheduler._last_candle_ts["EUR/USD"] == first_candles[-1].timestamp

        asyncio.run(scheduler._process_instrument("EUR/USD"))
        assert len(ledger.pending()) == 1
        assert scheduler._last_candle_ts["EUR/USD"] == second_candles[-1].timestamp


def test_provider_failure_does_not_crash_scheduler(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )
    scheduler._running = True

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]
    result = _live_analysis_result(candles, direction="BULLISH", confidence=1.0)

    call_count = 0

    async def fake_analyze(instrument: Instrument, timeframe: str, count: int) -> LiveAnalysisResult:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("provider failure")  # noqa: TRY002
        return result

    with patch.object(live_analysis, "analyze", fake_analyze):
        asyncio.run(scheduler._tick())
        asyncio.run(scheduler._tick())

    assert call_count == 3
    assert len(ledger.all()) == 1


def test_analysis_exception_does_not_crash_scheduler(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )
    scheduler._running = True

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]
    result = _live_analysis_result(candles, direction="BULLISH", confidence=1.0)

    call_count = 0

    async def fake_analyze(instrument: Instrument, timeframe: str, count: int) -> LiveAnalysisResult:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("analysis failure")  # noqa: TRY002
        return result

    with patch.object(live_analysis, "analyze", fake_analyze):
        asyncio.run(scheduler._tick())
        asyncio.run(scheduler._tick())

    assert call_count == 3
    assert len(ledger.all()) == 1


def _instrument(symbol: str = "EUR/USD") -> Instrument:
    return Instrument(symbol=symbol)


def _candle(ts: datetime, close: float) -> Candle:
    return Candle(
        instrument=_instrument(),
        timestamp=ts,
        timeframe="M1",
        open=close - 0.0005,
        high=close + 0.0005,
        low=close - 0.0005,
        close=close,
    )


def _live_analysis_result(candles: list[Candle], direction: str = "BULLISH", confidence: float = 0.8) -> LiveAnalysisResult:
    from src.data.models import AnalysisResult

    analysis = AnalysisResult(
        instrument=_instrument(),
        timestamp=candles[-1].timestamp,
        direction=direction,
        confidence=confidence,
        reason="test",
        trend="BULLISH",
        momentum="POSITIVE",
        volatility="NORMAL",
        rsi=60.0,
        ema_fast=1.0,
        ema_slow=0.999,
        price_action="BULLISH",
        overall_bias="BULLISH",
    )
    return LiveAnalysisResult(
        instrument=_instrument(),
        timeframe="M1",
        timestamp=candles[-1].timestamp,
        latest_price=candles[-1].close,
        analysis=analysis,
        candles=candles,
    )


def test_end_to_end_lifecycle_pending_to_win(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = TelegramFormatter()
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    signal_candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]
    signal_result = _live_analysis_result(signal_candles, direction="BULLISH", confidence=1.0)

    expiry_candle = _candle(base.replace(minute=40), 1.0 + 40 * 0.001 + 0.0005)
    expiry_candles = signal_candles + [expiry_candle]
    expiry_result = _live_analysis_result(expiry_candles, direction="BULLISH", confidence=1.0)

    with patch.object(live_analysis, "analyze", AsyncMock(side_effect=[signal_result, expiry_result])):
        asyncio.run(scheduler._process_instrument("EUR/USD"))
        asyncio.run(scheduler._resolve_pending_signals(Instrument(symbol="EUR/USD")))

    signal_id = f"EUR/USD_{signal_candles[-1].timestamp.strftime('%Y%m%d%H%M%S')}"
    loaded = ledger.get_by_id(signal_id)
    assert loaded is not None
    assert loaded.state == SignalState.RESOLVED
    assert loaded.outcome == SignalOutcome.WIN
    assert loaded.entry_price == signal_candles[-1].close
    assert loaded.exit_price == expiry_candle.close
    assert loaded.price_change == round(expiry_candle.close - signal_candles[-1].close, 5)

    text = formatter.format_signal_result(loaded)
    assert "WIN" in text
    assert signal_candles[-1].timestamp.strftime("%H:%M UTC") in formatter.format_signal(loaded, loaded.entry_price)


def test_end_to_end_lifecycle_pending_to_loss(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = TelegramFormatter()
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    signal_candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]
    signal_result = _live_analysis_result(signal_candles, direction="BULLISH", confidence=1.0)

    expiry_candle = _candle(base.replace(minute=40), 1.0 + 40 * 0.001 - 0.002)
    expiry_candles = signal_candles + [expiry_candle]
    expiry_result = _live_analysis_result(expiry_candles, direction="BULLISH", confidence=1.0)

    with patch.object(live_analysis, "analyze", AsyncMock(side_effect=[signal_result, expiry_result])):
        asyncio.run(scheduler._process_instrument("EUR/USD"))
        asyncio.run(scheduler._resolve_pending_signals(Instrument(symbol="EUR/USD")))

    signal_id = f"EUR/USD_{signal_candles[-1].timestamp.strftime('%Y%m%d%H%M%S')}"
    loaded = ledger.get_by_id(signal_id)
    assert loaded is not None
    assert loaded.state == SignalState.RESOLVED
    assert loaded.outcome == SignalOutcome.LOSS
    assert loaded.entry_price == signal_candles[-1].close
    assert loaded.exit_price == expiry_candle.close


def test_end_to_end_lifecycle_pending_to_draw(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = TelegramFormatter()
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    signal_candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]
    signal_result = _live_analysis_result(signal_candles, direction="BULLISH", confidence=1.0)

    expiry_candle = _candle(base.replace(minute=40), signal_candles[-1].close)
    expiry_candles = signal_candles + [expiry_candle]
    expiry_result = _live_analysis_result(expiry_candles, direction="BULLISH", confidence=1.0)

    with patch.object(live_analysis, "analyze", AsyncMock(side_effect=[signal_result, expiry_result])):
        asyncio.run(scheduler._process_instrument("EUR/USD"))
        asyncio.run(scheduler._resolve_pending_signals(Instrument(symbol="EUR/USD")))

    signal_id = f"EUR/USD_{signal_candles[-1].timestamp.strftime('%Y%m%d%H%M%S')}"
    loaded = ledger.get_by_id(signal_id)
    assert loaded is not None
    assert loaded.state == SignalState.RESOLVED
    assert loaded.outcome == SignalOutcome.DRAW
    assert loaded.entry_price == signal_candles[-1].close
    assert loaded.exit_price == expiry_candle.close


def test_persistence_reload_preserves_signal(tmp_path: Path) -> None:
    store = SignalLedgerStore(output_dir=tmp_path)
    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    signal = PaperSignal(
        id="persist_signal",
        instrument=_instrument(),
        timeframe="M1",
        timestamp=base,
        entry_price=1.17300,
        direction="BULLISH",
        confidence=0.82,
        state=SignalState.PENDING,
        outcome=SignalOutcome.PENDING,
        expiry_periods=1,
        expiry_timestamp=base + timedelta(minutes=1),
    )
    store.add_signal(signal)

    reloaded = SignalLedgerStore(output_dir=tmp_path)
    loaded = reloaded.get_by_id("persist_signal")
    assert loaded is not None
    assert loaded.entry_price == 1.17300
    assert loaded.state == SignalState.PENDING
    assert loaded.outcome == SignalOutcome.PENDING


def test_resolve_updates_existing_record_not_duplicate(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    signal_candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]
    signal_result = _live_analysis_result(signal_candles, direction="BULLISH", confidence=1.0)

    expiry_candle = _candle(base.replace(minute=40), 1.0 + 40 * 0.001 + 0.0005)
    expiry_candles = signal_candles + [expiry_candle]
    expiry_result = _live_analysis_result(expiry_candles, direction="BULLISH", confidence=1.0)

    with patch.object(live_analysis, "analyze", AsyncMock(side_effect=[signal_result, expiry_result])):
        asyncio.run(scheduler._process_instrument("EUR/USD"))
        asyncio.run(scheduler._resolve_pending_signals(Instrument(symbol="EUR/USD")))

    signal_id = f"EUR/USD_{signal_candles[-1].timestamp.strftime('%Y%m%d%H%M%S')}"
    all_signals = ledger.all()
    matching = [s for s in all_signals if s.id == signal_id]
    assert len(matching) == 1
    assert matching[0].state == SignalState.RESOLVED


def test_telegram_signal_and_result_share_identity(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = TelegramFormatter()
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    signal_candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]
    signal_result = _live_analysis_result(signal_candles, direction="BULLISH", confidence=1.0)

    with patch.object(live_analysis, "analyze", AsyncMock(return_value=signal_result)):
        asyncio.run(scheduler._process_instrument("EUR/USD"))

    signal = ledger.pending()[0]
    signal_text = formatter.format_signal(signal, signal_candles[-1].close)
    assert str(signal.instrument) in signal_text
    assert signal.direction in signal_text
    assert f"{signal.entry_price:.5f}" in signal_text
    assert signal.timestamp.strftime("%H:%M UTC") in signal_text

    ledger.update_signal(signal.id, state=SignalState.RESOLVED, outcome=SignalOutcome.WIN, exit_price=1.17350)
    resolved = ledger.get_by_id(signal.id)
    result_text = formatter.format_signal_result(resolved)
    assert str(resolved.instrument) in result_text
    assert resolved.direction in result_text
    assert f"{resolved.entry_price:.5f}" in result_text


def test_market_data_failure_does_not_persist_signal(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )
    scheduler._running = True

    async def fake_analyze(instrument: Instrument, timeframe: str, count: int) -> LiveAnalysisResult:
        raise Exception("market data failure")  # noqa: TRY002

    with patch.object(live_analysis, "analyze", fake_analyze):
        asyncio.run(scheduler._tick())
        asyncio.run(scheduler._tick())

    assert len(ledger.all()) == 0


def test_analysis_failure_does_not_persist_signal(tmp_path: Path) -> None:
    provider = MockMarketDataProvider()
    market_service = LiveMarketDataService(provider=provider)
    engine = AnalysisEngine()
    live_analysis = LiveAnalysisService(market_service=market_service, analysis_engine=engine)
    chart_gen = MagicMock(spec=ChartGenerator)
    chart_gen.generate_candlestick_chart.return_value = "/tmp/chart.png"
    ledger = SignalLedgerStore(output_dir=tmp_path)
    formatter = MagicMock(spec=TelegramFormatter)
    scheduler = LiveSignalScheduler(
        market_service=market_service,
        analysis_engine=engine,
        live_analysis=live_analysis,
        chart_generator=chart_gen,
        ledger=ledger,
        formatter=formatter,
        send_callback=MagicMock(),
        instruments=["EUR/USD"],
        interval_seconds=60,
        expiry_periods=1,
        confidence_threshold=0.0,
        enabled=True,
    )
    scheduler._running = True

    base = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = [_candle(base.replace(minute=i), 1.0 + i * 0.001) for i in range(40)]

    call_count = 0

    async def fake_analyze(instrument: Instrument, timeframe: str, count: int) -> LiveAnalysisResult:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("analysis failure")  # noqa: TRY002
        return _live_analysis_result(candles, direction="BULLISH", confidence=1.0)

    with patch.object(live_analysis, "analyze", fake_analyze):
        asyncio.run(scheduler._tick())
        asyncio.run(scheduler._tick())

    assert call_count == 3
    assert len(ledger.all()) == 1
