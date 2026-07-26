"""Plotly visualizations for strategy and benchmark performance."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import DEFAULT_CONFIG, BacktestConfig
from src.metrics import compute_drawdown_series


def plot_equity_curves(
    strategy_capital: pd.Series,
    benchmark_capital: pd.Series,
    initial_capital: float = DEFAULT_CONFIG.initial_capital,
    save_path: Path | None = None,
) -> go.Figure:
    """Plot portfolio growth for strategy vs benchmark."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=strategy_capital.index,
            y=strategy_capital.values,
            mode="lines",
            name="Mean Reversion Strategy",
            line={"width": 2},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=benchmark_capital.index,
            y=benchmark_capital.values,
            mode="lines",
            name="DIA Buy & Hold",
            line={"width": 2, "dash": "dash"},
        )
    )
    fig.update_layout(
        title=f"Portfolio Growth (${initial_capital:,.0f} Initial Investment)",
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        template="plotly_white",
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    fig.update_yaxes(tickformat="$,.0f")

    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(save_path))

    return fig


def plot_drawdowns(
    strategy_capital: pd.Series,
    benchmark_capital: pd.Series,
    save_path: Path | None = None,
) -> go.Figure:
    """Plot underwater drawdown curves for strategy and benchmark."""
    strategy_dd = compute_drawdown_series(strategy_capital) * 100.0
    benchmark_dd = compute_drawdown_series(benchmark_capital) * 100.0

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=strategy_dd.index,
            y=strategy_dd.values,
            mode="lines",
            name="Mean Reversion Strategy",
            fill="tozeroy",
            line={"width": 1.5},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=benchmark_dd.index,
            y=benchmark_dd.values,
            mode="lines",
            name="DIA Buy & Hold",
            fill="tozeroy",
            line={"width": 1.5, "dash": "dash"},
        )
    )
    fig.update_layout(
        title="Drawdown Over Time",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        template="plotly_white",
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    fig.update_yaxes(ticksuffix="%")

    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(save_path))

    return fig


def show_performance_charts(
    strategy_capital: pd.Series,
    benchmark_capital: pd.Series,
    config: BacktestConfig = DEFAULT_CONFIG,
    save_html: bool = True,
) -> tuple[go.Figure, go.Figure]:
    """Create and display equity and drawdown charts."""
    equity_path = config.data_dir / "equity_curve.html" if save_html else None
    drawdown_path = config.data_dir / "drawdown_chart.html" if save_html else None

    equity_fig = plot_equity_curves(
        strategy_capital=strategy_capital,
        benchmark_capital=benchmark_capital,
        initial_capital=config.initial_capital,
        save_path=equity_path,
    )
    drawdown_fig = plot_drawdowns(
        strategy_capital=strategy_capital,
        benchmark_capital=benchmark_capital,
        save_path=drawdown_path,
    )

    equity_fig.show()
    drawdown_fig.show()
    return equity_fig, drawdown_fig
