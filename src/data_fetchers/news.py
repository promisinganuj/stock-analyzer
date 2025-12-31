import requests
from datetime import date, timedelta
from src.utils.config import FINNHUB_KEY
from src.utils.logging import LOG

def fetch_news(symbol: str, days: int = 7):
    if not FINNHUB_KEY:
        raise RuntimeError("FINNHUB_KEY not set in environment")
    to_dt = date.today()
    from_dt = to_dt - timedelta(days=days)
    url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={from_dt.isoformat()}&to={to_dt.isoformat()}&token={FINNHUB_KEY}"
    LOG.info("Fetching news for %s", symbol)
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()
