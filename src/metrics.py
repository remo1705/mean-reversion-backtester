"""Institutional performance metrics for backtest results."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.config import DEFAULT_CONFIG, BacktestConfig


@dataclass(frozen=True)
class PerformanceMetrics:
    """Summary statistics for a capital or equity curve."""

    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    annual_turnover: float


def compute_drawdown_series(capital: pd.Series) -> pd.Series:
    """Compute drawdown percentage over time."""
    running_max = capital.cummax()
    return (capital - running_max) / running_max


def _annualized_return(capital: pd.Series, trading_days: int) -> float:
    if len(capital) < 2:
        return 0.0
    total_return = float(capital.iloc[-1] / capital.iloc[0])
    years = max(len(capital) / trading_days, 1 / trading_days)
    return total_return ** (1.0 / years) - 1.0


def _annualized_volatility(daily_returns: pd.Series, trading_days: int) -> float:
    if daily_returns.empty:
        return 0.0
    return float(daily_returns.std(ddof=0) * math.sqrt(trading_days))


def _sortino_ratio(
    annualized_return: float,
    daily_returns: pd.Series,
    risk_free_rate: float,
    trading_days: int,
) -> float:
    downside = daily_returns[daily_returns < 0]
    if downside.empty:
        return float("inf") if annualized_return > risk_free_rate else 0.0

    downside_std = float(downside.std(ddof=0) * math.sqrt(trading_days))
    if downside_std == 0:
        return float("inf") if annualized_return > risk_free_rate else 0.0
    return (annualized_return - risk_free_rate) / downside_std


def compute_metrics(
    capital: pd.Series,
    traded_notional: pd.Series | None = None,
    config: BacktestConfig = DEFAULT_CONFIG,
) -> PerformanceMetrics:
    """Calculate institutional risk/return metrics from a capital series."""
    capital = capital.astype(float)
    daily_returns = capital.pct_change().dropna()
    trading_days = config.trading_days_per_year

    ann_return = _annualized_return(capital, trading_days)
    ann_vol = _annualized_volatility(daily_returns, trading_days)
    sharpe = 0.0 if ann_vol == 0 else (ann_return - config.risk_free_rate) / ann_vol
    sortino = _sortino_ratio(ann_return, daily_returns, config.risk_free_rate, trading_days)
    max_dd = float(compute_drawdown_series(capital).min()) if not capital.empty else 0.0
    win_rate = float((daily_returns > 0).mean()) if not daily_returns.empty else 0.0

    years = max(len(capital) / trading_days, 1 / trading_days)
    if traded_notional is not None and not traded_notional.empty:
        avg_capital = float(capital.mean())
        annual_turnover = float(traded_notional.sum() / avg_capital / years) if avg_capital > 0 else 0.0
    else:
        annual_turnover = 0.0

    return PerformanceMetrics(
        annualized_return=ann_return,
        annualized_volatility=ann_vol,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown=max_dd,
        win_rate=win_rate,
        annual_turnover=annual_turnover,
    )


def format_metrics_table(
    strategy_metrics: PerformanceMetrics,
    benchmark_metrics: PerformanceMetrics | None = None,
) -> str:
    """Format metrics as a clean side-by-side text table."""
    headers = ["Metric", "Strategy"]
    rows: list[tuple[str, str, str | None]] = []

    if benchmark_metrics is not None:
        headers.append("DIA Benchmark")

    def _row(label: str, strategy_value: str, benchmark_value: str | None = None) -> tuple[str, str, str | None]:
        return label, strategy_value, benchmark_value

    benchmark = benchmark_metrics
    rows.extend(
        [
            _row("Annualized Return", f"{strategy_metrics.annualized_return:.2%}", None if benchmark is None else f"{benchmark.annualized_return:.2%}"),
            _row("Annualized Volatility", f"{strategy_metrics.annualized_volatility:.2%}", None if benchmark is None else f"{benchmark.annualized_volatility:.2%}"),
            _row("Sharpe Ratio", f"{strategy_metrics.sharpe_ratio:.2f}", None if benchmark is None else f"{benchmark.sharpe_ratio:.2f}"),
            _row("Sortino Ratio", f"{strategy_metrics.sortino_ratio:.2f}", None if benchmark is None else f"{benchmark.sortino_ratio:.2f}"),
            _row("Max Drawdown", f"{strategy_metrics.max_drawdown:.2%}", None if benchmark is None else f"{benchmark.max_drawdown:.2%}"),
            _row("Win Rate", f"{strategy_metrics.win_rate:.2%}", None if benchmark is None else f"{benchmark.win_rate:.2%}"),
            _row("Annual Turnover", f"{strategy_metrics.annual_turnover:.2f}x", None if benchmark is None else f"{benchmark.annual_turnover:.2f}x"),
        ]
    )

    col_widths = [max(len(headers[i]), max(len(row[i]) for row in rows)) for i in range(len(headers))]
    header_line = " | ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers))
    separator = "-+-".join("-" * width for width in col_widths)
    body = "\n".join(
        " | ".join(value.ljust(col_widths[i]) for i, value in enumerate(row[: len(headers)]))
        for row in rows
    )
    return f"{header_line}\n{separator}\n{body}"


def print_metrics(metrics: PerformanceMetrics, title: str = "Strategy Performance") -> None:
    """Print a single-strategy metrics summary."""
    print(f"\n{title}")
    print(format_metrics_table(metrics))


if __name__ == "__main__":
    sample = pd.Series(np.linspace(100_000, 120_000, 252))
    print_metrics(compute_metrics(sample), title="Sample Metrics")
