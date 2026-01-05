import requests
import pandas as pd
from src.utils.config import ALPHA_VANTAGE_KEY, PRICE_PROVIDER
from src.utils.logging import LOG

from src.data_fetchers.prices_stooq import fetch_price_history_stooq

def fetch_price_history(symbol: str, outputsize: str = "compact") -> pd.DataFrame:
    if PRICE_PROVIDER == "stooq":
        return fetch_price_history_stooq(symbol)

    if PRICE_PROVIDER in {"alpha_vantage", "alphavantage"}:
        if not ALPHA_VANTAGE_KEY:
            raise RuntimeError("ALPHA_VANTAGE_KEY not set in environment")
    else:
        raise ValueError(f"Unknown PRICE_PROVIDER={PRICE_PROVIDER!r}")

    url = (
        "https://www.alphavantage.co/query"
        f"?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize={outputsize}&apikey={ALPHA_VANTAGE_KEY}"
    )
    LOG.info("Fetching price history for %s", symbol)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    ts = data.get("Time Series (Daily)", {})
    if not ts:
        LOG.warning("No time series found in response for %s: %s", symbol, data.get('Note') or data)
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame.from_dict(ts, orient="index").sort_index()
    # columns are like "1. open", "4. close" => normalize names
    df = df.rename(columns=lambda c: c.split(". ")[1] if ". " in c else c)
    df.index = pd.to_datetime(df.index)

    # AlphaVantage daily fields: open/high/low/close/volume
    for col in ("open", "high", "low", "close"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    # Keep a consistent column set.
    keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    if not keep:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    return df[keep]
