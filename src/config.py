"""Application configuration and tunable constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class BacktestConfig:
    """Central configuration for the mean reversion backtester."""

    initial_capital: float = 100_000.0
    years_of_data: int = 10
    rolling_window: int = 20
    num_picks: int = 10
    friction_rate: float = 0.0005  # 5 bps per side (buy/sell)
    risk_free_rate: float = 0.02  # 2% annual
    benchmark_ticker: str = "DIA"
    wikipedia_url: str = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
    data_dir: Path = PROJECT_ROOT / "data"
    constituents_file: str = "dow_jones_constituents.csv"
    prices_file: str = "dow_jones_data.csv"
    trading_days_per_year: int = 252

    @property
    def constituents_path(self) -> Path:
        return self.data_dir / self.constituents_file

    @property
    def prices_path(self) -> Path:
        return self.data_dir / self.prices_file


DEFAULT_CONFIG = BacktestConfig()
