import os
import json
from src.agent import tools
from src.agent.prompts import SYSTEM_PROMPT
from src.utils.logging import LOG
from src.analysis.fundamentals import fundamentals_summary
from src.analysis.technicals import technical_summary
from src.data_fetchers.prices import fetch_price_history
# We use the OpenAI python package but expect Azure OpenAI-compatible endpoint via env vars.
from openai import AzureOpenAI, OpenAI
from src.utils.config import AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT

# Initialize the OpenAI client with proper SSL verification enabled
# If you encounter SSL certificate issues, fix them at the system level:
#   - Install/update certifi: pip install --upgrade certifi
#   - Update CA certificates on your system
#   - For corporate proxies, configure SSL_CERT_FILE environment variable
if AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT:
    client = AzureOpenAI(
        api_key=AZURE_OPENAI_KEY,
        api_version="2024-06-01",
        azure_endpoint=AZURE_OPENAI_ENDPOINT
    )
else:
    # Fallback to regular OpenAI
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )

TOOL_MAP = {
    "get_price": tools.tool_get_price,
    "get_technicals": tools.tool_get_technicals,
    "get_fundamentals": tools.tool_get_fundamentals,
    "get_news": tools.tool_get_news,
    "get_events": tools.tool_get_events
}

def analyze_stock(symbol: str):
    LOG.info("Starting analysis for %s", symbol)
    # Fetch price history once and compute technicals from it to reduce API calls.
    price_df = fetch_price_history(symbol)
    tech = technical_summary(price_df)
    fund = TOOL_MAP["get_fundamentals"](symbol)
    news = TOOL_MAP["get_news"](symbol)
    events = TOOL_MAP["get_events"](symbol)

    news_highlights = []
    if isinstance(news, list):
        for item in news[:6]:
            news_highlights.append(
                {
                    "headline": item.get("headline") or item.get("title"),
                    "source": item.get("source"),
                    "datetime": item.get("datetime") or item.get("date"),
                    "url": item.get("url"),
                }
            )

    event_highlights = []
    if isinstance(events, list):
        for item in events[:6]:
            event_highlights.append(
                {
                    "date": item.get("date") or item.get("fiscalDateEnding"),
                    "epsEstimated": item.get("epsEstimated") or item.get("epsEstimate"),
                    "revenueEstimated": item.get("revenueEstimated") or item.get("revenueEstimate"),
                }
            )

    fund_summary = fundamentals_summary(fund)

    # Prepare a compact context for the LLM
    context = {
        "symbol": symbol,
        "technical": tech,
        "fundamentals": fund_summary,
        "recent_news_count": len(news) if isinstance(news, list) else 0,
        "upcoming_events_count": len(events) if isinstance(events, list) else 0,
        "news_highlights": news_highlights,
        "event_highlights": event_highlights,
    }

    # Build prompt
    prompt = SYSTEM_PROMPT + "\n\nContext:\n" + json.dumps(context, indent=2)

    # Call LLM
    LOG.info("Calling LLM for %s", symbol)
    try:
        response = client.chat.completions.create(
            model=os.getenv('OPENAI_ENGINE', 'gpt-4o'),
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": "Please analyze this context:\n" + json.dumps(context)}],
            max_tokens=600,
            temperature=0.0
        )
        text = response.choices[0].message.content
    except Exception as e:
        LOG.exception("LLM call failed: %s", e)
        text = "LLM analysis unavailable: " + str(e)

    # Provide a compact, UI-friendly price history payload for charting without re-fetch.
    price_history = []
    try:
        if price_df is not None and not price_df.empty:
            tmp = price_df.tail(400).copy()
            tmp = tmp.reset_index().rename(columns={"index": "date"})
            tmp["date"] = tmp["date"].dt.strftime("%Y-%m-%d")
            price_history = tmp.to_dict(orient="records")
    except Exception:
        price_history = []

    return {
        "context": context,
        "llm_analysis": text,
        "raw_news": news,
        "raw_events": events,
        "price_history": price_history,
        "news_highlights": news_highlights,
        "event_highlights": event_highlights,
    }
