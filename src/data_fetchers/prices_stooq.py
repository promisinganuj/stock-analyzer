from __future__ import annotations

import io

import pandas as pd
import requests

from src.utils.logging import LOG


def _to_stooq_symbol(symbol: str) -> str:
    s = (symbol or "").strip().lower()
    if not s:
        raise ValueError("symbol is required")
    return s if s.endswith(".us") else f"{s}.us"


def fetch_price_history_stooq(symbol: str) -> pd.DataFrame:
    """Fetch US stock daily OHLCV from Stooq.

    Returns a DataFrame indexed by date with columns: open, high, low, close, volume.
    On missing/empty data, returns an empty DataFrame with the expected columns.
    """

    stooq_symbol = _to_stooq_symbol(symbol)
    url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"

    LOG.info("Fetching Stooq EOD history for %s", symbol)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()

    text = (resp.text or "").strip()
    if not text:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    # Occasionally a bad request may return HTML.
    if text[:20].lower().startswith("<!doctype html") or text[:6].lower().startswith("<html"):
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.read_csv(io.StringIO(text))
    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = df.rename(columns={c: c.strip().lower() for c in df.columns})
    if "date" not in df.columns:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").set_index("date")

    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    if not keep:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    return df[keep]
