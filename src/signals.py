"""Signal generation: daily returns and z-score based stock selection."""

from __future__ import annotations

import pandas as pd

from src.config import DEFAULT_CONFIG, BacktestConfig


def calculate_daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily returns from adjusted close prices."""
    return prices.pct_change()


def calculate_z_scores(
    returns: pd.DataFrame,
    window: int = DEFAULT_CONFIG.rolling_window,
) -> pd.DataFrame:
    """Calculate rolling z-scores of daily returns for each stock."""
    rolling_mean = returns.rolling(window=window).mean()
    rolling_std = returns.rolling(window=window).std()
    return (returns - rolling_mean) / rolling_std


def select_worst_performers(
    z_scores: pd.DataFrame,
    num_picks: int = DEFAULT_CONFIG.num_picks,
    warmup: int = DEFAULT_CONFIG.rolling_window,
) -> pd.DataFrame:
    """Select the lowest z-score stocks for each trading day.

    Skips the initial warmup period where rolling metrics are NaN.
    Dates with fewer than ``num_picks`` valid z-scores are omitted.

    Returns:
        Long-format DataFrame with columns: date, symbol, z_score, rank.
    """
    valid_scores = z_scores.iloc[warmup:]
    records: list[dict[str, object]] = []

    for date, row in valid_scores.iterrows():
        day_scores = row.dropna().sort_values()
        if len(day_scores) < num_picks:
            continue

        worst = day_scores.head(num_picks)
        for rank, (symbol, score) in enumerate(worst.items(), start=1):
            records.append(
                {
                    "date": pd.Timestamp(date),
                    "symbol": symbol,
                    "z_score": float(score),
                    "rank": rank,
                }
            )

    if not records:
        return pd.DataFrame(columns=["date", "symbol", "z_score", "rank"])

    picks = pd.DataFrame.from_records(records)
    picks["date"] = pd.to_datetime(picks["date"])
    return picks.sort_values(["date", "rank"]).reset_index(drop=True)


def generate_signals(
    prices: pd.DataFrame,
    config: BacktestConfig = DEFAULT_CONFIG,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate returns, z-scores, and daily worst-performer picks."""
    returns = calculate_daily_returns(prices)
    z_scores = calculate_z_scores(returns, window=config.rolling_window)
    picks = select_worst_performers(
        z_scores,
        num_picks=config.num_picks,
        warmup=config.rolling_window,
    )
    return returns, z_scores, picks


if __name__ == "__main__":
    from src.data_loader import ensure_data

    price_data = ensure_data()
    _, _, daily_picks = generate_signals(price_data)
    print(f"Generated {len(daily_picks)} pick rows across {daily_picks['date'].nunique()} days.")
