"""CLI entry point for the mean reversion backtester."""

from __future__ import annotations

import argparse

from src.backtester import run_backtest
from src.benchmark import compare_with_benchmark, print_comparison
from src.config import DEFAULT_CONFIG
from src.data_loader import ensure_data
from src.metrics import compute_metrics, print_metrics
from src.signals import generate_signals
from src.visualization import show_performance_charts


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run the DJIA mean reversion backtester.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-download constituents and price data from Wikipedia/yfinance.",
    )
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Skip Plotly chart rendering.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the full backtesting pipeline."""
    args = parse_args()
    config = DEFAULT_CONFIG

    print("Loading DJIA data...")
    prices = ensure_data(refresh=args.refresh, config=config)

    print("Generating z-score signals...")
    _, _, picks = generate_signals(prices, config=config)

    print("Running MOC backtest...")
    results = run_backtest(picks, prices, config=config)

    strategy_capital = results.set_index("date")["capital"]
    strategy_metrics = compute_metrics(
        strategy_capital,
        traded_notional=results.set_index("date")["traded_notional"],
        config=config,
    )
    print_metrics(strategy_metrics)

    print("\nBenchmarking against DIA...")
    strategy_metrics, benchmark_metrics, benchmark_capital = compare_with_benchmark(
        results,
        config=config,
    )
    print_comparison(strategy_metrics, benchmark_metrics)

    if not args.no_charts:
        print("\nRendering performance charts...")
        show_performance_charts(strategy_capital, benchmark_capital, config=config)


if __name__ == "__main__":
    main()
