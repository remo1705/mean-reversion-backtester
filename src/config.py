"""Application configuration and constants for the mean reversion backtester."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
CONSTITUENTS_CSV = DATA_DIR / "dow_jones_constituents.csv"
PRICES_CSV = DATA_DIR / "dow_jones_data.csv"

INITIAL_CAPITAL = 100_000.0
YEARS_OF_DATA = 10
ROLLING_WINDOW = 20
NUM_PICKS = 10
FRICTION_RATE = 0.0005  # 5 bps per side (buy or sell)
RISK_FREE_RATE = 0.02  # 2% annual
BENCHMARK_TICKER = "DIA"
TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class BacktestConfig:
    """Tunable parameters for the mean reversion backtest."""

    initial_capital: float = INITIAL_CAPITAL
    years_of_data: int = YEARS_OF_DATA
    rolling_window: int = ROLLING_WINDOW
    num_picks: int = NUM_PICKS
    friction_rate: float = FRICTION_RATE
    risk_free_rate: float = RISK_FREE_RATE
    benchmark_ticker: str = BENCHMARK_TICKER
    trading_days_per_year: int = TRADING_DAYS_PER_YEAR


DEFAULT_CONFIG = BacktestConfig()
