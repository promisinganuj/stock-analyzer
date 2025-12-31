import logging
import azure.functions as func
from src.data_fetchers.news import fetch_news
from src.storage.cache import save

def main(mytimer: func.TimerRequest) -> None:
    symbols = ["AAPL", "MSFT", "NVDA"]
    for sym in symbols:
        try:
            news = fetch_news(sym, days=7)
            save(f"news_{sym}", news)
        except Exception as e:
            logging.exception("Failed to fetch news for %s: %s", sym, e)
