from src.data_fetchers.prices import fetch_price_history
from src.data_fetchers.fundamentals import fetch_fundamentals
from src.data_fetchers.news import fetch_news
from src.data_fetchers.events import fetch_events
from src.analysis.technicals import technical_summary

def tool_get_price(symbol: str):
    df = fetch_price_history(symbol)
    return df.tail(500).to_dict()

def tool_get_technicals(symbol: str):
    df = fetch_price_history(symbol)
    return technical_summary(df)

def tool_get_fundamentals(symbol: str):
    return fetch_fundamentals(symbol)

def tool_get_news(symbol: str):
    return fetch_news(symbol)

def tool_get_events(symbol: str):
    return fetch_events(symbol)
