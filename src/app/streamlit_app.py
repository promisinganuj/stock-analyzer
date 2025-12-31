import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path for `src.*` imports when running via Streamlit.
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import streamlit as st

from src.agent.orchestrator import analyze_stock
from src.utils.logging import LOG


def _fmt_money(value) -> str:
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except Exception:
        return str(value)

    abs_number = abs(number)
    if abs_number >= 1_000_000_000_000:
        return f"${number/1_000_000_000_000:.2f}T"
    if abs_number >= 1_000_000_000:
        return f"${number/1_000_000_000:.2f}B"
    if abs_number >= 1_000_000:
        return f"${number/1_000_000:.2f}M"
    return f"${number:,.0f}"


def _fmt_dt(value) -> str:
    if value is None:
        return ""
    try:
        # Finnhub uses Unix seconds in `datetime`
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d")
        return str(value)
    except Exception:
        return str(value)


def _pct(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{value*100:.1f}%"
    except Exception:
        return "—"


def _fmt_signed_pct(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{value*100:+.1f}%"
    except Exception:
        return "—"


def _safe_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _fmt_float(value, decimals: int = 2) -> str:
    number = _safe_float(value)
    if number is None:
        return "—"
    return f"{number:.{decimals}f}"


def _df(dataframe: pd.DataFrame, **kwargs):
    """Render a dataframe with forward-compatible sizing."""
    try:
        return st.dataframe(dataframe, width="stretch", **kwargs)
    except TypeError:
        return st.dataframe(dataframe, use_container_width=True, **kwargs)


def _line(dataframe: pd.DataFrame, **kwargs):
    """Render a line chart with forward-compatible sizing."""
    try:
        return st.line_chart(dataframe, width="stretch", **kwargs)
    except TypeError:
        return st.line_chart(dataframe, use_container_width=True, **kwargs)


def _extract_markdown_section(md: str, heading: str) -> str | None:
    if not md:
        return None
    lines = md.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().lower() == f"## {heading}".lower():
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].strip().startswith("## "):
            end = j
            break
    section = "\n".join(lines[start:end]).strip()
    return section or None


def _recommendations(technical: dict, fundamentals: dict) -> tuple[str, str, list[str]]:
    rsi = _safe_float((technical or {}).get("rsi"))
    trend = ((technical or {}).get("trend") or "").lower()
    ema50 = _safe_float((technical or {}).get("ema50"))
    ema200 = _safe_float((technical or {}).get("ema200"))
    pe = _safe_float((fundamentals or {}).get("peRatio"))

    reasons: list[str] = []

    # Short-term: lean on momentum + RSI.
    if trend == "bullish":
        short = "Bullish bias (momentum)"
        reasons.append("EMA50 > EMA200 suggests upward momentum")
    elif trend == "bearish":
        short = "Bearish bias (momentum)"
        reasons.append("EMA50 < EMA200 suggests downward momentum")
    else:
        short = "Neutral (insufficient trend signal)"

    if rsi is not None:
        if rsi >= 70:
            short = "Cautious (overbought risk)"
            reasons.append("RSI ≥ 70 can indicate overbought conditions")
        elif rsi <= 30:
            short = "Opportunistic (oversold bounce risk/reward)"
            reasons.append("RSI ≤ 30 can indicate oversold conditions")

    # Long-term: combine trend + valuation (very rough).
    if trend == "bullish" and (pe is None or pe <= 30):
        long = "Constructive (trend supportive; valuation not extreme)"
        if pe is not None:
            reasons.append(f"P/E ≈ {pe:.1f} (rough valuation check)")
    elif trend == "bearish" and (pe is not None and pe >= 35):
        long = "Cautious (trend weak; valuation elevated)"
        reasons.append(f"P/E ≈ {pe:.1f} (may be elevated vs many sectors)")
    elif trend == "bearish":
        long = "Cautious (trend weak)"
    else:
        long = "Neutral (needs more confirmation)"

    # Add a sanity reason if EMAs missing.
    if ema50 is None or ema200 is None:
        reasons.append("EMA signals may be less reliable with limited history")

    return short, long, reasons


st.set_page_config(page_title="AI Stock Research Agent", layout="wide")
st.title("📈 AI Stock Research Agent")
st.markdown(
    "Analyze stock performance using AI-powered tools. Enter a ticker and run analysis."
)


with st.sidebar:
    st.header("🔍 Stock")
    symbol = st.text_input(
        "Stock symbol (e.g., AAPL)",
        value="AAPL",
        key="stock_symbol_input",
    ).strip().upper()
    run = st.button("Analyze", key="analyze_button", use_container_width=True)


if run:
    with st.spinner("Running analysis…"):
        try:
            # Cache at the Streamlit layer by storing in session_state.
            st.session_state["analysis_result"] = analyze_stock(symbol)
        except Exception as exc:
            LOG.exception("Error during analysis")
            st.session_state["analysis_result"] = None
            st.error(f"Error during analysis: {exc}")


result = st.session_state.get("analysis_result")
if not result:
    st.info("Enter a ticker in the sidebar and click Analyze.")
    st.stop()

context = result.get("context") or {}
technical = context.get("technical") or {}
fundamentals = context.get("fundamentals") or {}
news_highlights = result.get("news_highlights") or context.get("news_highlights") or []
event_highlights = result.get("event_highlights") or context.get("event_highlights") or []


st.subheader("Overview")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Symbol", context.get("symbol", symbol))
col2.metric("Last Close", f"${technical.get('close', float('nan')):.2f}" if technical.get("close") is not None else "—")
col3.metric("Trend", (technical.get("trend") or "—").title())
col4.metric("RSI (14)", f"{technical.get('rsi', float('nan')):.1f}" if technical.get("rsi") is not None else "—")


st.subheader("Price")
prices_payload = result.get("price_history") or []
prices = pd.DataFrame(prices_payload)
if not prices.empty and "date" in prices.columns:
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    prices = prices.dropna(subset=["date"]).sort_values("date").set_index("date")

if not prices.empty and "close" in prices.columns:
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices = prices.dropna(subset=["close"])

if not prices.empty:
    # Prefer the richer metrics from technical_summary (computed once in orchestrator).
    pcol1, pcol2, pcol3, pcol4, pcol5 = st.columns(5)
    pcol1.metric("1W", _fmt_signed_pct(technical.get("return_5d")))
    pcol2.metric("1M", _fmt_signed_pct(technical.get("return_21d")))
    pcol3.metric("3M", _fmt_signed_pct(technical.get("return_63d")))
    pcol4.metric("YTD", _fmt_signed_pct(technical.get("return_ytd")))
    pcol5.metric("Max DD (1y)", _fmt_signed_pct(technical.get("max_drawdown_252d")))

    # Plot Close with EMA50 overlay.
    ema50_series = prices["close"].ewm(span=50, adjust=False).mean()
    chart_df = pd.DataFrame({"Close": prices["close"], "EMA50": ema50_series})
    _line(chart_df)

    with st.expander("Signals"):
        scol1, scol2, scol3, scol4 = st.columns(4)
        scol1.metric("RSI Band", (technical.get("rsi_band") or "—").title())
        scol2.metric("Dist to EMA50", _fmt_signed_pct(technical.get("dist_to_ema50")))
        scol3.metric("Dist to EMA200", _fmt_signed_pct(technical.get("dist_to_ema200")))
        scol4.metric("Vol (21d)", _pct(technical.get("vol_21d")))

        mcol1, mcol2, mcol3 = st.columns(3)
        mcol1.metric("MACD", _fmt_float(technical.get("macd"), decimals=3))
        mcol2.metric("Signal", _fmt_float(technical.get("macd_signal"), decimals=3))
        mcol3.metric("Hist", _fmt_float(technical.get("macd_hist"), decimals=3))

    with st.expander("Show recent closes"):
        _df(prices.tail(30))
else:
    st.info("No price history available.")


left, right = st.columns(2)

with left:
    st.subheader("Fundamentals")
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    fcol1.metric("Market Cap", _fmt_money(fundamentals.get("marketCap")))
    fcol2.metric("P/E (TTM)", str(fundamentals.get("peRatio") or "—"))
    fcol3.metric("EPS (TTM)", _fmt_float(fundamentals.get("epsTTM"), decimals=2))
    fcol4.metric("Dividend Yield", _pct(_safe_float(fundamentals.get("dividendYieldTTM"))))

    high_52w = _safe_float(fundamentals.get("52WeekHigh"))
    low_52w = _safe_float(fundamentals.get("52WeekLow"))
    if high_52w is not None or low_52w is not None:
        st.caption(
            "52W Range: "
            + (f"${low_52w:.2f}" if low_52w is not None else "—")
            + " – "
            + (f"${high_52w:.2f}" if high_52w is not None else "—")
        )

    with st.expander("Details"):
        if fundamentals:
            _fund_df = pd.DataFrame(
                [{"Field": k, "Value": v} for k, v in fundamentals.items()]
            )
            _fund_df = _fund_df.astype(str)
            _df(_fund_df, hide_index=True)
        else:
            st.write("No fundamentals summary available.")

with right:
    st.subheader("Technical")
    tcol1, tcol2, tcol3 = st.columns(3)
    tcol1.metric("EMA 50", f"${technical.get('ema50', float('nan')):.2f}" if technical.get("ema50") is not None else "—")
    tcol2.metric("EMA 200", f"${technical.get('ema200', float('nan')):.2f}" if technical.get("ema200") is not None else "—")
    tcol3.metric("News Count (7d)", str(context.get("recent_news_count") or 0))

    with st.expander("Details"):
        if technical:
            _tech_df = pd.DataFrame(
                [{"Metric": k, "Value": v} for k, v in technical.items()]
            )
            _tech_df = _tech_df.astype(str)
            _df(_tech_df, hide_index=True)
        else:
            st.write("No technical summary available.")


st.subheader("Recommendations")
short_rec, long_rec, rec_reasons = _recommendations(technical, fundamentals)
rc1, rc2 = st.columns(2)
rc1.metric("Short-term (days–weeks)", short_rec)
rc2.metric("Long-term (months+)", long_rec)
with st.expander("Why these recommendations?"):
    for reason in rec_reasons:
        st.write(f"- {reason}")


st.subheader("LLM Summary")
llm_md = result.get("llm_analysis") or ""
if llm_md:
    st.markdown(llm_md)
else:
    st.info("LLM analysis unavailable.")


st.subheader("Catalysts & Risks")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Upcoming catalysts (from events/news)**")
    if event_highlights:
        for ev in event_highlights[:5]:
            st.write(f"- {ev.get('date') or '—'} (EPS est: {ev.get('epsEstimated') or '—'})")
    elif news_highlights:
        for item in news_highlights[:5]:
            title = item.get("headline") or "(headline unavailable)"
            url = item.get("url")
            if url:
                st.markdown(f"- [{title}]({url})")
            else:
                st.write(f"- {title}")
    else:
        st.write("- —")

with c2:
    st.markdown("**Key risks (from LLM section)**")
    risks = _extract_markdown_section(llm_md, "Key Risks")
    if risks:
        st.markdown(risks)
    else:
        st.write("- —")


st.subheader("News")
raw_news = result.get("raw_news") or []
if isinstance(raw_news, list) and raw_news:
    for item in raw_news[:8]:
        headline = item.get("headline") or item.get("title") or "(no headline)"
        url = item.get("url")
        source = item.get("source") or ""
        dt = _fmt_dt(item.get("datetime") or item.get("date"))
        summary = item.get("summary") or ""

        if url:
            st.markdown(f"**[{headline}]({url})**")
        else:
            st.markdown(f"**{headline}**")
        st.caption(" · ".join([p for p in [dt, source] if p]))
        if summary:
            st.write(summary)
        st.divider()
else:
    st.info("No news items available.")


with st.expander("Raw data"):
    st.markdown("**Context**")
    st.json(context)
    st.markdown("**News (raw)**")
    st.write(raw_news)
    st.markdown("**Events (raw)**")
    st.write(result.get("raw_events") or [])


st.caption("For informational purposes only. Not financial advice.")
