"""MOC trading simulation with transaction friction."""

from __future__ import annotations

import math

import pandas as pd

from src.config import DEFAULT_CONFIG, BacktestConfig


def _build_trading_calendar(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Map each trading date to the next trading date."""
    calendar = pd.DataFrame({"date": dates})
    calendar["next_date"] = calendar["date"].shift(-1)
    return calendar


def _prepare_trade_rows(
    picks: pd.DataFrame,
    prices: pd.DataFrame,
) -> pd.DataFrame:
    """Attach entry and exit prices to each daily pick via calendar merge."""
    calendar = _build_trading_calendar(prices.index)
    trade_rows = picks.merge(calendar, on="date", how="inner")
    trade_rows = trade_rows.dropna(subset=["next_date"])

    price_long = prices.stack(future_stack=True).rename("price").reset_index()
    price_long.columns = ["date", "symbol", "price"]

    entry_prices = price_long.rename(columns={"date": "entry_date", "price": "entry_price"})
    exit_prices = price_long.rename(columns={"date": "exit_date", "price": "exit_price"})

    trade_rows = trade_rows.merge(
        entry_prices,
        left_on=["date", "symbol"],
        right_on=["entry_date", "symbol"],
        how="left",
    )
    trade_rows = trade_rows.merge(
        exit_prices,
        left_on=["next_date", "symbol"],
        right_on=["exit_date", "symbol"],
        how="left",
    )
    return trade_rows


def run_backtest(
    picks: pd.DataFrame,
    prices: pd.DataFrame,
    config: BacktestConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    """Simulate MOC mean-reversion trades with friction costs.

    On day T, allocate current equity equally across the 10 worst z-score picks,
    buy at close(T), and liquidate at close(T+1).
    """
    if picks.empty:
        raise ValueError("No trade picks provided for backtest.")

    trade_rows = _prepare_trade_rows(picks, prices)
    capital = config.initial_capital
    records: list[dict[str, object]] = []

    for trade_date, day_picks in trade_rows.groupby("date", sort=True):
        day_picks = day_picks.sort_values("rank")
        if len(day_picks) != config.num_picks:
            continue

        if capital <= 0 or not math.isfinite(capital):
            continue

        if day_picks[["entry_price", "exit_price"]].isna().any().any():
            records.append(
                {
                    "date": pd.Timestamp(trade_date),
                    "capital": capital,
                    "daily_return": 0.0,
                    "traded_notional": 0.0,
                    "num_trades": 0,
                }
            )
            continue

        allocation = capital / config.num_picks
        proceeds_total = 0.0
        traded_notional = 0.0

        for _, pick in day_picks.iterrows():
            entry_price = float(pick["entry_price"])
            exit_price = float(pick["exit_price"])
            if entry_price <= 0 or exit_price <= 0:
                proceeds_total = float("nan")
                break

            buy_cash = allocation * (1.0 - config.friction_rate)
            shares = buy_cash / entry_price
            sell_proceeds = shares * exit_price * (1.0 - config.friction_rate)
            proceeds_total += sell_proceeds
            traded_notional += allocation + sell_proceeds

        if not math.isfinite(proceeds_total) or proceeds_total <= 0:
            records.append(
                {
                    "date": pd.Timestamp(trade_date),
                    "capital": capital,
                    "daily_return": 0.0,
                    "traded_notional": 0.0,
                    "num_trades": 0,
                }
            )
            continue

        daily_return = (proceeds_total / capital) - 1.0
        capital = proceeds_total
        records.append(
            {
                "date": pd.Timestamp(trade_date),
                "capital": capital,
                "daily_return": daily_return,
                "traded_notional": traded_notional,
                "num_trades": config.num_picks,
            }
        )

    results = pd.DataFrame.from_records(records)
    if results.empty:
        raise ValueError("Backtest produced no results.")

    results["date"] = pd.to_datetime(results["date"])
    results = results.sort_values("date").reset_index(drop=True)

    final_capital = float(results["capital"].iloc[-1])
    total_return = (final_capital / config.initial_capital) - 1.0
    print(f"Final capital: ${final_capital:,.2f}")
    print(f"Total return: {total_return:.2%}")

    return results


if __name__ == "__main__":
    from src.data_loader import ensure_data
    from src.signals import generate_signals

    price_data = ensure_data()
    _, _, daily_picks = generate_signals(price_data)
    backtest_results = run_backtest(daily_picks, price_data)
    print(backtest_results.tail())
