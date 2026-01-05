import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Ensure project root is on sys.path for `src.*` imports when running pytest.
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def _reload_prices_module(price_provider: str | None):
    import importlib

    if price_provider is None:
        os.environ.pop("PRICE_PROVIDER", None)
    else:
        os.environ["PRICE_PROVIDER"] = price_provider

    import src.utils.config as config
    import src.data_fetchers.prices as prices

    importlib.reload(config)
    importlib.reload(prices)
    return prices


def test_price_provider_unset_preserves_alpha_vantage_error_when_key_missing(monkeypatch):
    # Prevent python-dotenv from repopulating the key from a local .env during reload.
    monkeypatch.setenv("ALPHA_VANTAGE_KEY", "")
    prices = _reload_prices_module(None)

    with pytest.raises(RuntimeError, match="ALPHA_VANTAGE_KEY not set"):
        prices.fetch_price_history("AAPL")


def test_price_provider_stooq_routes_to_stooq_backend(monkeypatch):
    # Even if Alpha Vantage key is missing, stooq should work when explicitly selected.
    monkeypatch.setenv("ALPHA_VANTAGE_KEY", "")
    prices = _reload_prices_module("stooq")

    fake_df = Mock()
    with patch.object(prices, "fetch_price_history_stooq", return_value=fake_df) as stooq:
        out = prices.fetch_price_history("AAPL")

    stooq.assert_called_once_with("AAPL")
    assert out is fake_df
