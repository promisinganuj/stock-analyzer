import requests
from src.utils.config import FMP_KEY
from src.utils.logging import LOG

def fetch_events(symbol: str):
    if not FMP_KEY:
        raise RuntimeError("FMP_KEY not set in environment")
    url = f"https://financialmodelingprep.com/stable/earnings?symbol={symbol}&apikey={FMP_KEY}"
    LOG.info("Fetching events for %s", symbol)
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()
