"""Data retrieval and loading for DJIA constituents and price history.

Note:
    Using current Wikipedia constituents introduces survivorship bias.
    Production backtests require point-in-time index membership datasets
    (e.g., Norgate, Bloomberg) to avoid this limitation.
"""

from __future__ import annotations

import json
import os
import ssl
import time
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from src.config import DEFAULT_CONFIG, BacktestConfig

# #region agent log
_DEBUG_LOG_PATH = Path(__file__).resolve().parent.parent / ".cursor" / "debug-583489.log"


def _agent_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    payload = {
        "sessionId": "583489",
        "runId": "post-fix",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")


# #endregion


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

    # #region agent log
    import sys

    verify_paths = ssl.get_default_verify_paths()
    openssl_cafile = verify_paths.openssl_cafile
    _agent_log(
        "A",
        "data_loader.py:fetch_constituents",
        "ssl_ca_bundle_state",
        {
            "python": sys.executable,
            "openssl_cafile": openssl_cafile,
            "openssl_cafile_exists": os.path.exists(openssl_cafile) if openssl_cafile else False,
            "SSL_CERT_FILE": os.environ.get("SSL_CERT_FILE"),
        },
    )
    # #endregion

    # requests uses certifi's CA bundle, avoiding macOS Python.org missing cert.pem
    response = requests.get(
        config.wikipedia_url,
        headers={"User-Agent": "mean-reversion-backtester/1.0"},
        timeout=30,
    )
    response.raise_for_status()

    # #region agent log
    _agent_log(
        "F",
        "data_loader.py:fetch_constituents",
        "requests_fetch_ok",
        {"status_code": response.status_code, "html_len": len(response.text)},
    )
    # #endregion

    tables = pd.read_html(StringIO(response.text), match="Symbol")
    # #region agent log
    _agent_log(
        "F",
        "data_loader.py:fetch_constituents",
        "read_html_ok",
        {
            "num_tables": len(tables),
            "columns": list(tables[0].columns) if tables else [],
        },
    )
    # #endregion
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

    # #region agent log
    _agent_log(
        "E",
        "data_loader.py:ensure_data",
        "cache_state",
        {
            "refresh": refresh,
            "constituents_exists": config.constituents_path.exists(),
            "prices_exists": config.prices_path.exists(),
            "will_fetch_constituents": refresh or not config.constituents_path.exists(),
        },
    )
    # #endregion

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
