import os
from dotenv import load_dotenv

load_dotenv()

ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")
FINNHUB_KEY = os.getenv("FINNHUB_KEY")
FMP_KEY = os.getenv("FMP_KEY")

# Data source routing (optional). Keep defaults unchanged unless explicitly set.
PRICE_PROVIDER = (os.getenv("PRICE_PROVIDER") or "").strip().lower()

AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
