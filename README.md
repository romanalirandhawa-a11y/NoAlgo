# NoAlgo

Telegram-based Live Market AI / Paper-Trading research bot.

## Prerequisites

- Python 3.10+
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- Market data provider API key (optional, only for live data)

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

Edit `.env` and set:
- `TELEGRAM_BOT_TOKEN`
- `MARKET_DATA_PROVIDER=mock` or `alpha_vantage`
- `MARKET_DATA_API_KEY` (only when using `alpha_vantage`)

## Run

```bash
python main.py
```

## Run tests

```bash
pytest
```

## Lint / type check

```bash
ruff check .
mypy .
```

## Market Data Provider

### Supported providers

- `mock` — local development/testing, no API key needed
- `alpha_vantage` — live forex data, requires `MARKET_DATA_API_KEY`
- `twelvedata` — live forex data, requires `TWELVEDATA_API_KEY`

### Alpha Vantage

**Why Alpha Vantage:**
- Free developer tier available
- Official, stable API
- Supports forex pairs with M1 timeframe
- Well documented
- No authentication complexity

**Limitations:**
- Free tier: 5 requests/minute, 500 requests/day
- M1 data may have slight delay
- Limited historical data depth on free tier
- Requires internet access
- Subject to Alpha Vantage terms of service

### Twelve Data

**Why Twelve Data:**
- Free Basic plan available
- Supports forex pairs with M1 timeframe
- Provides real-time and historical data
- No credit card required for Basic plan

**Limitations:**
- Free tier: 8 requests/minute, 800 requests/day
- M1 data may have slight delay
- Requires internet access
- Subject to Twelve Data terms of service

### Switching providers

Change `MARKET_DATA_PROVIDER` in `.env`:

Supported instruments for live data:
- EUR/USD
- GBP/USD
- USD/JPY
- AUD/USD

Supported timeframe: M1

## Analysis Engine

The analysis engine converts validated M1 candle data into a structured `AnalysisResult`.

### Indicators Used

- **EMA 9 / EMA 21** — exponential moving averages used to assess trend direction.
- **RSI 14** — relative strength index used to assess momentum extremes.
- **Momentum (5-period)** — close-to-close price change over the last 5 candles.
- **ATR 14** — average true range used to assess volatility.
- **Price Action** — recent candle direction, higher-high/lower-low behavior, and bullish candle ratio.

### Bias Classification

The engine classifies market state into:

- `trend`: BULLISH / BEARISH / NEUTRAL
- `momentum`: POSITIVE / NEGATIVE / NEUTRAL
- `volatility`: HIGH / LOW / NORMAL
- `price_action`: BULLISH / BEARISH / NEUTRAL
- `overall_bias`: BULLISH / BEARISH / NEUTRAL

### Confidence Interpretation

`confidence` is a deterministic **feature-agreement score**, calculated from how many non-neutral features agree with the `overall_bias`.

**Important:** Confidence does **not** represent a probability of profit, guaranteed accuracy, or win rate. It only reflects internal agreement among the selected technical features at the analysis timestamp.

### Data Requirements

- Minimum 30 candles for `GOOD` data quality.
- Fewer than 30 candles returns `LIMITED` or `INSUFFICIENT`.
- Missing or invalid candles are rejected; the engine never invents data.

### Backtesting / Look-Ahead Protection

- At candle N, analysis uses only candles `<= N`.
- The engine does not access future candles.
- Analysis timestamp is derived from the input snapshot, preserving chronological order.

### Dependencies

- `python-telegram-bot>=21.0,<23.0`
- `httpx>=0.27`
- `pydantic>=2.0`
- `python-dotenv>=1.0`
- `matplotlib>=3.7`

## Scheduler

The live paper signal scheduler is **disabled by default**. Enable it with `/startlive` in Telegram, or set `LIVE_SIGNAL_ENABLED=true` in `.env`.

## Smoke Tests (Optional)

### Telegram Smoke Test

If you have a valid `TELEGRAM_BOT_TOKEN`:

1. Set `MARKET_DATA_PROVIDER=mock` in `.env`
2. Run `python main.py`
3. In Telegram: send `/start`, `/status`, `/analyze`, `/live`
4. Confirm `/live` reports scheduler as disabled/stopped
5. Stop the bot cleanly with Ctrl+C

### Alpha Vantage Smoke Test

If you have a valid `MARKET_DATA_API_KEY`:

1. Set `MARKET_DATA_PROVIDER=alpha_vantage` and `MARKET_DATA_API_KEY=...` in `.env`
2. Run `python main.py`
3. In Telegram: send `/analyze EUR/USD`
4. Verify candles parse, timestamps are valid, analysis runs, chart is generated

## Limitations

- The engine is deterministic and rule-based.
- No AI/model prediction is implemented in this phase.
- No backtest performance report is generated yet.
- Confidence is not calibrated against historical outcomes.
- Real historical backtesting requires a legitimate historical M1 dataset.
- Alpha Vantage free-tier historical depth may be limited.
- If no dataset is available, local backtesting cannot be executed.
- Historical results do not guarantee future performance.
- Confidence is feature agreement, not probability of profit.
- The live scheduler defaults to disabled to prevent unintended paper-signal generation.

## Paper Trading Notice

This project is for **research and educational purposes only**. All signals are paper-only. No real money is traded. No broker execution is implemented. Do not use this software for actual trading decisions.

## OTC Data

No OTC (Over-The-Counter) data scraping is implemented. The project uses only official exchange data via Alpha Vantage or mock data for testing.

## Telegram Interface

### Commands

- `/start` — Start the bot
- `/help` — Show available commands
- `/status` — Show data feed status
- `/analyze [instrument]` — Run live market analysis for the default or specified instrument
- `/startlive` — Start live paper signal scheduler
- `/stoplive` — Stop live paper signal scheduler
- `/live` — Show live scheduler status

### /analyze Behavior

1. Validates the instrument against supported instruments.
2. Requests the latest market snapshot via the configured provider.
3. Runs the analysis engine on the received candles.
4. Generates a chart image with candlesticks, EMA 9, EMA 21, and current price.
5. Sends a compact professional analysis message.
6. Sends the chart image separately.

If the provider cannot return data, the bot replies with:

⚠️ Live market data is currently unavailable.

Please try again shortly.

### Chart

- Dark professional trading-dashboard theme.
- Candlestick chart with EMA 9 and EMA 21 overlays.
- Current price line and annotation.
- Saved to the configured `CHART_OUTPUT_DIR`.
- Unique filenames prevent overwrites.

### Confidence Notice

The confidence value shown in the Telegram message represents internal **feature agreement only**. It does **not** represent a probability of winning, profit guarantee, or accuracy guarantee.

## Backtesting

### Usage

```python
from src.backtesting.engine import BacktestEngine
from src.backtesting.models import BacktestConfig
from src.backtesting.metrics import compute_metrics
from src.backtesting.reporter import format_report
from src.data.models import Candle, Instrument

candles = [...]  # historical candle data
engine = BacktestEngine(analysis_engine=AnalysisEngine())
config = BacktestConfig(
    instrument=Instrument(symbol="EUR/USD"),
    timeframe="M1",
    expiry_periods=1,
    minimum_candles=30,
    confidence_threshold=0.7,
)
results = await engine.run(candles, config)
metrics = compute_metrics(results)
print(format_report(config, metrics))
```

### Look-Ahead Protection

- At candle index T, analysis uses only `candles[:T+1]`.
- Outcome is determined using only `candles[T + expiry_periods]`.
- Future candles never influence the generated `AnalysisResult`.

### Limitations

- Backtesting requires historical candle data.
- The current Alpha Vantage free tier may not provide sufficient historical M1 data for extensive backtests.
- Deterministic test fixtures are provided for unit tests.
- Results are historical evaluations only and do not guarantee future performance.
- Confidence buckets are descriptive, not predictive.

## Historical Data

### CSV Format

Place CSV files in the configured `HISTORICAL_DATA_DIR` or provide an explicit path.

Required columns:
- `timestamp` — ISO-like format: `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DDTHH:MM:SS`
- `open`
- `high`
- `low`
- `close`

Optional columns:
- `volume`
- `instrument`

Example:
```csv
timestamp,open,high,low,close,volume
2024-01-01 00:00:00,1.0,1.001,0.999,1.0005,100
2024-01-01 00:01:00,1.0005,1.002,1.0,1.001,110
```

### Data Validation

- Timestamps are normalized to UTC.
- Duplicate timestamps are rejected.
- OHLC relationships are validated.
- Chronological ordering is enforced.
- Gaps are reported but do not stop backtesting.
- Missing or malformed rows raise clear errors.
- No candles are fabricated.

### Backtest Runner

```python
from src.backtesting.runner import BacktestRunner
from src.backtesting.historical_data import CandleCSVReader
from src.backtesting.models import BacktestConfig
from src.data.models import Instrument

reader = CandleCSVReader(instrument=Instrument(symbol="EUR/USD"), timeframe="M1")
candles = reader.load("data/historical/eurusd_m1.csv")

runner = BacktestRunner(output_dir="data/backtests")
config = BacktestConfig(
    instrument=Instrument(symbol="EUR/USD"),
    timeframe="M1",
    expiry_periods=1,
    minimum_candles=30,
    confidence_threshold=0.7,
    start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
    end_time=datetime(2024, 6, 1, tzinfo=timezone.utc),
)
metrics, report = await runner.run(candles, config)
print(report)
```

### Date Ranges and Out-of-Sample Validation

- Use `start_time` and `end_time` to define the evaluation window.
- For out-of-sample validation, split historical data chronologically and run separate backtests.
- Do not use the same period both to tune rules and to report final performance.

### Session Breakdown

When sufficient data is available, the report includes descriptive UTC-hour breakdowns:
- signals
- wins
- losses
- draws
- win rate

This is research information only. No hour is labeled as “best” or recommended.

### Limitations

- Real historical backtesting requires a legitimate historical M1 dataset.
- Alpha Vantage free-tier historical depth may be limited.
- If no dataset is available, local backtesting cannot be executed.
- Historical results do not guarantee future performance.
- Confidence is feature agreement, not probability of profit.
