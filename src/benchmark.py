"""Benchmark comparison against the DIA ETF."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from src.config import DEFAULT_CONFIG, BacktestConfig
from src.metrics import PerformanceMetrics, compute_metrics, format_metrics_table


def fetch_benchmark_prices(
    start: pd.Timestamp,
    end: pd.Timestamp,
    ticker: str = DEFAULT_CONFIG.benchmark_ticker,
) -> pd.Series:
    """Fetch adjusted close prices for the benchmark ETF."""
    history = yf.Ticker(ticker).history(
        start=start,
        end=end + pd.Timedelta(days=1),
        auto_adjust=True,
    )
    if history.empty:
        raise ValueError(f"No benchmark data returned for {ticker}.")

    prices = history["Close"].copy()
    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    prices.name = ticker
    return prices.sort_index()


def build_buy_and_hold_curve(
    prices: pd.Series,
    initial_capital: float = DEFAULT_CONFIG.initial_capital,
) -> pd.Series:
    """Build a buy-and-hold equity curve from benchmark prices."""
    returns = prices.pct_change().fillna(0.0)
    growth = (1.0 + returns).cumprod()
    return initial_capital * growth


def compare_with_benchmark(
    strategy_results: pd.DataFrame,
    config: BacktestConfig = DEFAULT_CONFIG,
) -> tuple[PerformanceMetrics, PerformanceMetrics, pd.Series]:
    """Compare strategy performance against a DIA buy-and-hold benchmark."""
    strategy_capital = strategy_results.set_index("date")["capital"]
    start = strategy_capital.index.min()
    end = strategy_capital.index.max()

    benchmark_prices = fetch_benchmark_prices(start=start, end=end, ticker=config.benchmark_ticker)
    benchmark_prices = benchmark_prices.loc[
        (benchmark_prices.index >= start) & (benchmark_prices.index <= end)
    ]

    benchmark_capital = build_buy_and_hold_curve(
        benchmark_prices,
        initial_capital=config.initial_capital,
    )

    aligned = pd.concat(
        [strategy_capital, benchmark_capital],
        axis=1,
        join="inner",
    )
    aligned.columns = ["strategy", "benchmark"]

    strategy_metrics = compute_metrics(
        aligned["strategy"],
        traded_notional=strategy_results.set_index("date")["traded_notional"],
        config=config,
    )
    benchmark_metrics = compute_metrics(aligned["benchmark"], config=config)
    return strategy_metrics, benchmark_metrics, aligned["benchmark"]


def print_comparison(
    strategy_metrics: PerformanceMetrics,
    benchmark_metrics: PerformanceMetrics,
) -> None:
    """Print side-by-side strategy vs benchmark metrics and verdict."""
    print("\nStrategy vs DIA Benchmark")
    print(format_metrics_table(strategy_metrics, benchmark_metrics))

    if strategy_metrics.sharpe_ratio > benchmark_metrics.sharpe_ratio:
        print(
            "\nThe mean reversion strategy outperformed the Dow Jones (DIA) "
            "on a risk-adjusted basis (Sharpe ratio)."
        )
    elif strategy_metrics.sharpe_ratio < benchmark_metrics.sharpe_ratio:
        print(
            "\nThe Dow Jones (DIA) outperformed the mean reversion strategy "
            "on a risk-adjusted basis (Sharpe ratio)."
        )
    else:
        print("\nThe mean reversion strategy matched DIA on a risk-adjusted basis (Sharpe ratio).")


if __name__ == "__main__":
    from src.backtester import run_backtest
    from src.data_loader import ensure_data
    from src.signals import generate_signals

    prices = ensure_data()
    _, _, picks = generate_signals(prices)
    results = run_backtest(picks, prices)
    strategy, benchmark, _ = compare_with_benchmark(results)
    print_comparison(strategy, benchmark)
