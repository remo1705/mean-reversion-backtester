# Mean Reversion Backtester

A modular Python backtester that tests a daily mean-reversion strategy on Dow Jones Industrial Average (DJIA) constituents and compares results against the DIA ETF benchmark.

## Strategy Overview

Each trading day, the strategy:

1. Computes rolling 20-day z-scores of daily returns for each DJIA stock.
2. Selects the 10 stocks with the most negative z-scores (statistical losers).
3. Buys an equal-weight portfolio at the market-on-close (MOC) price.
4. Liquidates all positions at the next day's close.
5. Applies 5 basis points of friction on every buy and sell (10 bps round-trip).

Initial capital: **$100,000**.

## Important Caveat: Survivorship Bias

This project uses **current** DJIA constituents from Wikipedia applied to historical price data. Stocks removed from the index over the backtest period are excluded, which introduces survivorship bias. Production systems should use point-in-time constituent datasets (e.g., Norgate, Bloomberg).

## Setup

```bash
cd ~/Projects/mean-reversion-backtester
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Run with cached CSV data (if available)
python main.py

# Re-download constituents and prices
python main.py --refresh

# Skip Plotly charts
python main.py --no-charts
```

## Project Structure

```
mean-reversion-backtester/
├── main.py                 # CLI orchestrator
├── data/                   # Generated CSV/HTML outputs (gitignored)
└── src/
    ├── config.py           # Tunable constants
    ├── data_loader.py      # Wikipedia + yfinance data retrieval
    ├── signals.py          # Returns, z-scores, daily picks
    ├── backtester.py       # MOC simulation with friction
    ├── metrics.py          # Sharpe, Sortino, drawdown, turnover
    ├── benchmark.py        # DIA comparison
    └── visualization.py    # Plotly equity and drawdown charts
```

## Sample Output

```
Final capital: $112,345.67
Total return: 12.35%

Strategy Performance
Metric               | Strategy
---------------------+---------
Annualized Return    | 8.42%
Annualized Volatility| 12.15%
Sharpe Ratio         | 0.53
Sortino Ratio        | 0.71
Max Drawdown         | -15.32%
Win Rate             | 52.10%
Annual Turnover      | 48.50x

Strategy vs DIA Benchmark
...
The mean reversion strategy outperformed the Dow Jones (DIA) on a risk-adjusted basis (Sharpe ratio).
```

## Dependencies

- pandas, numpy, yfinance, plotly, lxml

## License

MIT
