# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Stock Research Agent - an agent-based system performing technical analysis, fundamental analysis, news & events ingestion, and LLM-based stock recommendations.

Built with Python, Streamlit frontend, Azure OpenAI integration, and example Azure Functions for scheduled data fetching.

## Environment Setup

1. Copy `.env.example` to `.env` and fill in API keys:
   - `ALPHA_VANTAGE_KEY` - for price history
   - `FINNHUB_KEY` - for news data
   - `FMP_KEY` - for fundamentals data
   - `AZURE_OPENAI_KEY` and `AZURE_OPENAI_ENDPOINT` - for LLM analysis (or use `OPENAI_API_KEY` as fallback)

2. Create and activate virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .\.venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Streamlit Demo
```bash
streamlit run src/app/streamlit_app.py
```

### Docker
```bash
docker build -t stock-analyzer .
docker run -p 8501:8501 --env-file .env stock-analyzer
```

## Testing

Run tests with pytest:
```bash
pytest tests/
```

Run a specific test file:
```bash
pytest tests/test_analysis.py
```

## Architecture

### Core Data Flow

The system follows this orchestration pattern:

1. **Data Fetchers** (`src/data_fetchers/`) - Raw data ingestion from external APIs:
   - `prices.py` - Alpha Vantage daily price history
   - `fundamentals.py` - Financial metrics (P/E, market cap, etc.)
   - `news.py` - Recent headlines from Finnhub
   - `events.py` - Corporate events (earnings dates, estimates)

2. **Analysis Layer** (`src/analysis/`) - Transform raw data into signals:
   - `technicals.py` - Compute EMA50/200, RSI, MACD, volatility, drawdown, and returns (5d/21d/63d/252d/YTD)
   - `fundamentals.py` - Summarize fundamental metrics

3. **Agent Layer** (`src/agent/`) - Orchestration and LLM integration:
   - `orchestrator.py` - **Entry point** for stock analysis. Coordinates all fetchers, computes technicals once, assembles context, calls LLM for recommendations
   - `tools.py` - Tool wrappers around fetchers for potential function-calling workflows
   - `prompts.py` - System prompt defining LLM output structure (TL;DR, Short-Term/Long-Term recommendations, Catalysts, Risks, Confidence)

4. **UI Layer** (`src/app/streamlit_app.py`) - User interface:
   - Calls `analyze_stock()` from orchestrator
   - Displays price charts with EMA overlays, metrics, news, events, and LLM-generated markdown summary
   - Implements custom recommendation logic based on RSI, trend (EMA50 vs EMA200), and P/E ratio

### Important Design Patterns

**Single Price Fetch**: `orchestrator.analyze_stock()` fetches price history **once** and reuses the DataFrame for both technical analysis and UI charting. This minimizes API calls and ensures consistency.

**SSL Workaround**: A custom `httpx.Client(verify=False)` is used in `orchestrator.py` for Azure OpenAI calls due to macOS SSL issues. This is **for development only** and should be removed in production.

**Flexible LLM Client**: The orchestrator checks for Azure OpenAI credentials first, then falls back to standard OpenAI API if Azure is not configured.

**UI Recommendation Logic**: `streamlit_app.py:_recommendations()` generates short-term and long-term recommendations independent of the LLM. The LLM provides a structured markdown summary, while the UI combines both rule-based and LLM insights.

## Key Files

- `src/agent/orchestrator.py:analyze_stock()` - Main analysis orchestration function
- `src/analysis/technicals.py:technical_summary()` - Core technical indicator computation
- `src/app/streamlit_app.py` - Full Streamlit UI with charting and formatting
- `src/utils/config.py` - Centralized environment variable loading

## Azure Functions (Optional)

The `azure/` directory contains example Azure Functions for scheduled data fetching:
- `function_fetch_prices/` - Scheduled price data ingestion
- `function_fetch_news/` - Scheduled news ingestion
- `host.json`, `local.settings.json` - Azure Functions configuration

## Notes

- API providers (Alpha Vantage, Finnhub, FinancialModelingPrep) use free tiers by default. Replace with paid endpoints for production.
- Always display "not financial advice" disclaimers when exposing recommendations to users.
- The system uses pandas DataFrames extensively for time series manipulation.
- All technical indicators handle edge cases where insufficient data exists (short histories default to fractional spans).
