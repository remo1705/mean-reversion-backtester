# Mean Reversion Backtester

A modular Python backtester for a volatility-normalized mean-reversion strategy on Dow Jones Industrial Average (DJIA) constituents. It covers data acquisition, signal generation, MOC execution with transaction costs, risk metrics, DIA benchmarking, and interactive Plotly charts.

## Strategy

### Signals

Each trading day:

1. Compute daily returns from adjusted closes for each DJIA constituent.
2. Calculate a 20-day rolling z-score of returns:
   `z = (return − rolling mean) / rolling std`
3. Select the **10 stocks with the most negative z-scores** (statistically anomalous losers).

### Execution

| Feature | Specification |
|---------|---------------|
| Entry | Market-on-close (MOC) at day T close |
| Exit | Full liquidation at day T+1 close |
| Allocation | Equal weight across 10 picks |
| Friction | 5 bps per side (10 bps round-trip) |
| Initial capital | $100,000 |

## Risk Metrics

| Metric | Description |
|--------|-------------|
| Annualized return | Compounded annual growth rate |
| Annualized volatility | Std. dev. of daily returns × √252 |
| Sharpe ratio | (Return − Rf) / Volatility (Rf = 2%) |
| Sortino ratio | Return / downside deviation |
| Max drawdown | Largest peak-to-trough decline |
| Win rate | Share of days with positive returns |
| Annual turnover | Trading volume / average capital per year |

Results are compared against the **DIA** ETF over the same period.

## Limitations

| Limitation | Notes |
|------------|-------|
| Survivorship bias | Uses **current** Wikipedia DJIA constituents for the full history. Removed names are excluded. Production work needs point-in-time membership (e.g. Norgate, Bloomberg). |
| Long-only | Buys losers only; no shorting of winners. |
| Friction model | Flat 5 bps per side; no variable slippage or market impact. |
| Benchmark | Strategy risk profile differs from DIA — compare with care. |

## Setup

**Requires:** Python 3.10+ and an internet connection for the first data download.

```bash
git clone https://github.com/remo1705/mean-reversion-backtester.git
cd mean-reversion-backtester

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Usage

```bash
# Use cached CSVs under data/ when present
python main.py

# Re-download constituents (Wikipedia) and prices (yfinance)
python main.py --refresh

# Skip Plotly chart rendering (useful for headless runs)
python main.py --no-charts
```

On first run (or with `--refresh`), constituents are fetched with `requests` + `pandas.read_html`, and prices via `yfinance`. Outputs land in `data/`.

## Sample Output

```
Loading DJIA data...
Generating z-score signals...
Running MOC backtest...
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

Benchmarking against DIA...

Strategy vs DIA Benchmark
Metric               | Strategy | DIA Benchmark
---------------------+----------+--------------
Annualized Return    | 8.42%    | 13.09%
Annualized Volatility| 12.15%   | 17.57%
Sharpe Ratio         | 0.53     | 0.63
Sortino Ratio        | 0.71     | 0.75
Max Drawdown         | -15.32%  | -36.70%
Win Rate             | 52.10%   | 54.94%
Annual Turnover      | 48.50x   | 0.00x

The Dow Jones (DIA) outperformed the mean reversion strategy on a risk-adjusted basis (Sharpe ratio).

Rendering performance charts...
```

Numbers vary by period and data vintage. Charts are written as HTML under `data/` (equity curve and drawdown).

## Project Structure

```
mean-reversion-backtester/
├── main.py                 # CLI entry point
├── requirements.txt
├── README.md
├── data/                   # Generated CSVs / charts (gitignored)
│   ├── dow_jones_constituents.csv
│   ├── dow_jones_data.csv
│   ├── equity_curve.html
│   └── drawdown_chart.html
└── src/
    ├── config.py           # Tunable constants
    ├── data_loader.py      # Wikipedia + yfinance retrieval
    ├── signals.py          # Returns, z-scores, daily picks
    ├── backtester.py       # MOC simulation with friction
    ├── metrics.py          # Sharpe, Sortino, drawdown, turnover
    ├── benchmark.py        # DIA comparison
    └── visualization.py    # Plotly equity and drawdown charts
```

## Dependencies

```
pandas
numpy
yfinance
plotly
lxml
requests
```

## Reading the Results

| Signal | Interpretation |
|--------|----------------|
| Sharpe ≳ 0.5 | Positive risk-adjusted returns over the sample |
| Turnover ≫ 50× | Friction is a large drag on net performance |
| Large max drawdown | Path risk is material even if average returns look fine |
| Strategy vs DIA | Prefer Sharpe / drawdown context over raw return alone |

## Possible Extensions

- Short the top z-score winners alongside long losers
- Regime splits (bull / bear / sideways)
- Parameter search over window length and pick count
- Sector or concentration constraints
- Richer cost models (impact, variable slippage)

## License

MIT License
