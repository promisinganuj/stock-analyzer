import requests
from src.utils.config import FINNHUB_KEY
from src.utils.config import FMP_KEY
from src.utils.logging import LOG

def fetch_finnhub_metrics(symbol: str):
    if not FINNHUB_KEY:
        raise RuntimeError("FINNHUB_KEY not set in environment")
    url = (
        "https://finnhub.io/api/v1/stock/metric"
        f"?symbol={symbol}&metric=all&token={FINNHUB_KEY}"
    )
    LOG.info("Fetching Finnhub metrics for %s", symbol)
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()

def fetch_fundamentals(symbol: str):
    if not FMP_KEY:
        raise RuntimeError("FMP_KEY not set in environment")
    url = f"https://financialmodelingprep.com/stable/profile?symbol={symbol}&apikey={FMP_KEY}"
    LOG.info("Fetching fundamentals for %s", symbol)
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    fmp_profile = r.json()

    finnhub_metrics = None
    try:
        finnhub_metrics = fetch_finnhub_metrics(symbol)
    except Exception as exc:
        # Optional enrichment; do not fail the whole pipeline.
        LOG.warning("Could not fetch Finnhub metrics for %s: %s", symbol, exc)

    return {
        "fmp_profile": fmp_profile,
        "finnhub_metrics": finnhub_metrics,
    }
