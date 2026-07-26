"""Data retrieval and loading for DJIA constituents and price history.

Note:
    Using current Wikipedia constituents introduces survivorship bias.
    Production backtests require point-in-time index membership datasets
    (e.g., Norgate, Bloomberg) to avoid this limitation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

from src.config import DEFAULT_CONFIG, BacktestConfig


def _normalize_symbol(symbol: str) -> str:
    """Clean and normalize a ticker symbol for yfinance."""
    cleaned = symbol.replace("\xa0", "").strip()
    for prefix in ("NYSE:", "NASDAQ:"):
        cleaned = cleaned.replace(prefix, "")
    cleaned = cleaned.strip()
    return cleaned.replace(".", "-")


def fetch_constituents(
    save_path: Path | None = None,
    config: BacktestConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    """Fetch current DJIA constituents from Wikipedia and save to CSV.

    Args:
        save_path: Optional override for the output CSV path.
        config: Backtest configuration.

    Returns:
        DataFrame with columns ``symbol`` and ``company`` (when available).
    """
    output_path = save_path or config.constituents_path
    tables = pd.read_html(config.wikipedia_url, match="Symbol")
    if not tables:
        raise ValueError("Could not find DJIA constituents table on Wikipedia.")

    components = tables[0].copy()
    if "Symbol" not in components.columns:
        raise ValueError("Constituents table is missing a Symbol column.")

    company_col = next(
        (col for col in ("Company", "Security", "Name") if col in components.columns),
        None,
    )

    constituents = pd.DataFrame(
        {
            "symbol": components["Symbol"].map(_normalize_symbol),
            "company": components[company_col] if company_col else "",
        }
    )
    constituents = constituents.drop_duplicates(subset="symbol").reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    constituents.to_csv(output_path, index=False)
    return constituents


def fetch_price_history(
    symbols: list[str],
    save_path: Path | None = None,
    config: BacktestConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    """Fetch daily adjusted close prices for each symbol via yfinance.

    Args:
        symbols: List of ticker symbols.
        save_path: Optional override for the output CSV path.
        config: Backtest configuration.

    Returns:
        Wide DataFrame indexed by date with one column per symbol.
    """
    output_path = save_path or config.prices_path
    period = f"{config.years_of_data}y"
    price_frames: dict[str, pd.Series] = {}

    for symbol in symbols:
        try:
            history = yf.Ticker(symbol).history(period=period, auto_adjust=True)
            if history.empty or "Close" not in history.columns:
                print(f"Error fetching {symbol}: no price data returned")
                continue
            closes = history["Close"].copy()
            closes.index = pd.to_datetime(closes.index).tz_localize(None)
            closes.name = symbol
            price_frames[symbol] = closes
        except Exception as exc:
            print(f"Error fetching {symbol}: {exc}")

    if not price_frames:
        raise ValueError("No price history could be fetched for any symbol.")

    prices = pd.concat(price_frames.values(), axis=1)
    prices.index.name = "Date"
    prices = prices.sort_index()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(output_path)
    return prices


def load_constituents(path: Path | None = None, config: BacktestConfig = DEFAULT_CONFIG) -> list[str]:
    """Load constituent symbols from a CSV file."""
    csv_path = path or config.constituents_path
    df = pd.read_csv(csv_path)
    if "symbol" not in df.columns:
        raise ValueError(f"Constituents file {csv_path} is missing a symbol column.")
    return df["symbol"].astype(str).tolist()


def load_prices(path: Path | None = None, config: BacktestConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """Load price history from CSV with a datetime index."""
    csv_path = path or config.prices_path
    prices = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    prices.index = pd.to_datetime(prices.index)
    prices.index.name = "Date"
    return prices.sort_index()


def load_and_fill_prices(
    path: Path | None = None,
    config: BacktestConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    """Load prices and forward-fill missing values."""
    prices = load_prices(path=path, config=config)
    return prices.ffill()


def ensure_data(
    refresh: bool = False,
    config: BacktestConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    """Fetch or load DJIA data, optionally refreshing cached CSV files."""
    config.data_dir.mkdir(parents=True, exist_ok=True)

    if refresh or not config.constituents_path.exists():
        constituents = fetch_constituents(config=config)
        symbols = constituents["symbol"].tolist()
    else:
        symbols = load_constituents(config=config)

    if refresh or not config.prices_path.exists():
        fetch_price_history(symbols, config=config)

    return load_and_fill_prices(config=config)


if __name__ == "__main__":
    data = ensure_data(refresh=True)
    print(f"Loaded {data.shape[1]} symbols across {len(data)} trading days.")
