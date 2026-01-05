import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

# Ensure project root is on sys.path for `src.*` imports when running pytest.
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.data_fetchers.prices_stooq import _to_stooq_symbol, fetch_price_history_stooq


def test_to_stooq_symbol_appends_us_suffix():
    assert _to_stooq_symbol("AAPL") == "aapl.us"
    assert _to_stooq_symbol("msft") == "msft.us"
    assert _to_stooq_symbol("brk-b") == "brk-b.us"


def test_fetch_price_history_stooq_parses_csv():
    csv = """Date,Open,High,Low,Close,Volume\n2026-01-02,100,105,99,104,123456\n2026-01-03,104,106,101,102,222\n"""

    resp = Mock()
    resp.text = csv
    resp.raise_for_status = Mock()

    with patch("src.data_fetchers.prices_stooq.requests.get", return_value=resp) as get:
        df = fetch_price_history_stooq("AAPL")

    get.assert_called_once()
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert df.index.dtype.kind == "M"  # datetime
    assert float(df.iloc[-1]["close"]) == 102.0


def test_fetch_price_history_stooq_handles_html_response():
    resp = Mock()
    resp.text = "<!doctype html><html><body>nope</body></html>"
    resp.raise_for_status = Mock()

    with patch("src.data_fetchers.prices_stooq.requests.get", return_value=resp):
        df = fetch_price_history_stooq("AAPL")

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.empty
