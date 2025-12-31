# AI Stock Research Agent (Azure + Python)

A modular agent-based stock research system that performs:

- Technical analysis
- Fundamental analysis
- News & events ingestion
- LLM-based explanation & recommendation

This is a starter scaffold — adapt data providers, models, and deployment for production.

## Quick start (local prototype)

1. Copy `.env.example` to `.env` and fill API keys.
2. Create a Python virtual environment and install requirements:
   ```
   python -m venv .venv
   source .venv/bin/activate   # or .\.venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
3. Run the Streamlit demo:
   ```
   streamlit run src/app/streamlit_app.py
   ```

## What’s included
- `src/` : core Python packages for fetchers, analysis, agent orchestration, and a simple Streamlit app.
- `azure/` : example Azure Functions entrypoints for scheduled fetches.
- `tests/` : minimal unit test stubs.
- `.env.example` : environment variables to configure.

## Notes
- This project uses free-tier-friendly APIs in examples (Alpha Vantage, Finnhub, FinancialModelingPrep). Replace with paid endpoints for production.
- Always add a clear "not financial advice" disclaimer when exposing recommendations to users.
