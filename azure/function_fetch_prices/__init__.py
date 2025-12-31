import logging
import azure.functions as func
from src.data_fetchers.prices import fetch_price_history
from src.storage.db import save_prices

def main(mytimer: func.TimerRequest) -> None:
    symbols = ["AAPL", "MSFT", "NVDA"]
    for sym in symbols:
        try:
            df = fetch_price_history(sym)
            save_prices(sym, df)
        except Exception as e:
            logging.exception("Failed to fetch/save for %s: %s", sym, e)
