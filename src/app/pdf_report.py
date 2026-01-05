from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


@dataclass(frozen=True)
class PdfReportOptions:
    title: str = "AI Stock Research Agent"
    include_news: bool = True
    max_table_rows: int = 18


def default_pdf_filename(symbol: str, generated_at: datetime | None = None) -> str:
    symbol_clean = (symbol or "UNKNOWN").strip().upper() or "UNKNOWN"
    ts = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return f"{symbol_clean}_analysis_{ts.strftime('%Y%m%d_%H%M')}.pdf"


def build_pdf_report_bytes(
    result: dict[str, Any],
    *,
    generated_at: datetime | None = None,
    options: PdfReportOptions | None = None,
) -> bytes:
    """Build a PDF report for a completed analysis.

    Pure function: does not perform network calls.
    """

    options = options or PdfReportOptions()
    context = (result or {}).get("context") or {}
    technical = context.get("technical") or {}
    fundamentals = context.get("fundamentals") or {}
    llm_text = (result or {}).get("llm_analysis") or ""
    symbol = context.get("symbol") or "UNKNOWN"
    company = fundamentals.get("companyName") or ""

    generated_at = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        title=f"{symbol} Analysis",
        author=options.title,
        pageCompression=0,
    )

    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    mono = ParagraphStyle(
        "Mono",
        parent=body,
        fontName="Courier",
        fontSize=9,
        leading=11,
    )

    story: list[Any] = []

    header_title = f"{symbol} — {company}" if company else str(symbol)
    story.append(Paragraph(header_title, h1))
    story.append(Paragraph(options.title, body))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M UTC')}", body))
    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            "Disclaimer: For informational purposes only. Not financial advice.",
            ParagraphStyle("Disclaimer", parent=body, textColor=colors.grey),
        )
    )
    story.append(Spacer(1, 14))

    # Summary table
    summary_rows = [
        ["Metric", "Value"],
        ["Last Close", _fmt_money_or_number(technical.get("close"), prefix="$", decimals=2)],
        ["Trend", _safe_str(technical.get("trend"))],
        ["RSI (14)", _fmt_money_or_number(technical.get("rsi"), decimals=1)],
        ["Market Cap", _fmt_market_cap(fundamentals.get("marketCap"))],
        ["P/E Ratio", _safe_str(fundamentals.get("peRatio"))],
        ["Beta", _fmt_money_or_number(fundamentals.get("beta"), decimals=2)],
    ]
    story.append(Paragraph("Overview", h2))
    story.append(_table(summary_rows, col_widths=(170, 360)))
    story.append(Spacer(1, 12))

    # Chart
    chart_bytes = _render_price_chart_png_bytes(result)
    if chart_bytes:
        story.append(Paragraph("Price Chart", h2))
        story.append(Spacer(1, 6))
        story.append(Image(BytesIO(chart_bytes), width=520, height=260))
        story.append(Spacer(1, 10))

    # Fundamentals + technicals tables
    story.append(Paragraph("Fundamental Metrics", h2))
    story.append(_kv_table(fundamentals, max_rows=options.max_table_rows))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Technical Metrics", h2))
    story.append(_kv_table(technical, max_rows=options.max_table_rows))

    # AI insights
    story.append(PageBreak())
    story.append(Paragraph("AI Insights", h2))
    story.append(Spacer(1, 6))
    if llm_text.strip():
        story.extend(_markdownish_to_paragraphs(llm_text, styles=styles))
    else:
        story.append(Paragraph("No AI insights available.", body))

    # News highlights (optional)
    if options.include_news:
        story.append(Spacer(1, 12))
        story.append(Paragraph("News & Catalysts", h2))
        story.append(Spacer(1, 6))
        news = (result or {}).get("news_highlights") or []
        if isinstance(news, list) and news:
            for item in news[:6]:
                headline = _safe_str(item.get("headline") or item.get("title") or "(headline unavailable)")
                source = _safe_str(item.get("source") or "")
                dt = _safe_str(item.get("datetime") or item.get("date") or "")
                line = headline
                if source or dt:
                    meta = " — ".join([p for p in [source, dt] if p])
                    line = f"{headline} ({meta})"
                story.append(Paragraph("• " + _escape(line), mono))
        else:
            story.append(Paragraph("No recent news items available.", body))

    doc.build(story)
    return buffer.getvalue()


def _table(rows: list[list[str]], *, col_widths: tuple[int, int] = (200, 330)) -> Table:
    t = Table(rows, colWidths=list(col_widths), hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


def _kv_table(payload: dict[str, Any], *, max_rows: int = 18) -> Table:
    if not isinstance(payload, dict) or not payload:
        return _table([["Field", "Value"], ["—", "—"]])

    rows: list[list[str]] = [["Field", "Value"]]
    for i, (k, v) in enumerate(payload.items()):
        if i >= max_rows:
            break
        rows.append([_escape(str(k)), _escape(_safe_str(v))])

    return _table(rows)


def _markdownish_to_paragraphs(md: str, *, styles) -> list[Any]:
    """Very small subset of markdown rendering into paragraphs."""

    body = styles["BodyText"]
    blocks: list[Any] = []
    for raw_line in (md or "").splitlines():
        line = raw_line.strip("\n")
        if not line.strip():
            blocks.append(Spacer(1, 6))
            continue
        if line.startswith("### "):
            blocks.append(Paragraph(_escape(line[4:].strip()), styles["Heading3"]))
            continue
        if line.startswith("## "):
            blocks.append(Paragraph(_escape(line[3:].strip()), styles["Heading2"]))
            continue
        if line.startswith("# "):
            blocks.append(Paragraph(_escape(line[2:].strip()), styles["Heading1"]))
            continue
        if line.startswith("- ") or line.startswith("• "):
            blocks.append(Paragraph("• " + _escape(line[2:].strip()), body))
            continue
        blocks.append(Paragraph(_escape(line), body))

    return blocks


def _escape(text: str) -> str:
    # ReportLab Paragraph supports a small HTML subset; escape for safety.
    from xml.sax.saxutils import escape

    return escape(text or "")


def _safe_str(value: Any) -> str:
    if value is None:
        return "—"
    s = str(value).strip()
    return s if s else "—"


def _fmt_market_cap(value: Any) -> str:
    try:
        n = float(value)
    except Exception:
        return _safe_str(value)

    abs_n = abs(n)
    if abs_n >= 1_000_000_000_000:
        return f"${n/1_000_000_000_000:.2f}T"
    if abs_n >= 1_000_000_000:
        return f"${n/1_000_000_000:.2f}B"
    if abs_n >= 1_000_000:
        return f"${n/1_000_000:.2f}M"
    return f"${n:,.0f}"


def _fmt_money_or_number(value: Any, *, prefix: str = "", decimals: int = 2) -> str:
    if value is None or value == "":
        return "—"
    try:
        n = float(value)
        if decimals == 0:
            return f"{prefix}{n:,.0f}"
        return f"{prefix}{n:,.{decimals}f}"
    except Exception:
        return _safe_str(value)


def _render_price_chart_png_bytes(result: dict[str, Any]) -> bytes | None:
    prices_payload = (result or {}).get("price_history") or []
    if not isinstance(prices_payload, list) or not prices_payload:
        return None

    try:
        import pandas as pd

        df = pd.DataFrame(prices_payload)
        if df.empty or "close" not in df.columns:
            return None

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"]).sort_values("date")
            df = df.set_index("date")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df = df.dropna(subset=["close"]).tail(260)
        if df.empty:
            return None

        # Lazy import so tests can still run if matplotlib isn't installed yet.
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        ema50 = df["close"].ewm(span=50, adjust=False).mean()
        ema200 = df["close"].ewm(span=200, adjust=False).mean()

        fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=150)
        ax.plot(df.index, df["close"], label="Close", linewidth=1.2)
        ax.plot(df.index, ema50, label="EMA50", linewidth=1.0)
        ax.plot(df.index, ema200, label="EMA200", linewidth=1.0)
        ax.set_title("Price & Moving Averages")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="upper left", fontsize=7)
        fig.tight_layout()

        out = BytesIO()
        fig.savefig(out, format="png")
        plt.close(fig)
        return out.getvalue()
    except Exception:
        return None
