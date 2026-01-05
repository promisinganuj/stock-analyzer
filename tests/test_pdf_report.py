from datetime import datetime, timezone

from src.app.pdf_report import build_pdf_report_bytes


def test_build_pdf_report_bytes_contains_header_text():
    result = {
        "context": {
            "symbol": "AAPL",
            "technical": {
                "close": 200.12,
                "trend": "bullish",
                "rsi": 55.2,
            },
            "fundamentals": {
                "companyName": "Apple Inc.",
                "marketCap": 3_000_000_000_000,
                "peRatio": 28.5,
                "beta": 1.12,
            },
        },
        "llm_analysis": "## Summary\n- Solid momentum\n\n## Key Risks\n- Valuation\n",
        "price_history": [
            {"date": "2025-12-30", "close": 195.0},
            {"date": "2025-12-31", "close": 197.5},
            {"date": "2026-01-02", "close": 200.12},
        ],
        "news_highlights": [
            {"headline": "Apple announces earnings date", "source": "Example", "datetime": "2026-01-02"}
        ],
    }

    pdf_bytes = build_pdf_report_bytes(result, generated_at=datetime(2026, 1, 5, 1, 2, tzinfo=timezone.utc))

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert len(pdf_bytes) > 1000
    assert pdf_bytes[:4] == b"%PDF"

    # ReportLab output is uncompressed (pageCompression=0) so header text should appear.
    assert b"AAPL" in pdf_bytes
    assert b"Apple Inc." in pdf_bytes
