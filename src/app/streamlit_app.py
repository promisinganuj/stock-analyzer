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


def _colored_pct(value: float | None, inverse: bool = False) -> str:
    """Format percentage with color: green for positive, red for negative.

    Args:
        value: Numeric value as decimal (e.g., 0.05 for 5%)
        inverse: If True, negative is green (for metrics like drawdown where lower is better)

    Returns:
        Formatted colored percentage string
    """
    if value is None:
        return "—"
    color = "green" if value >= 0 else "red"
    if inverse:
        color = "red" if value >= 0 else "green"
    return f":{color}[{value*100:+.1f}%]"


def _colored_trend(trend: str | None) -> str:
    """Format trend with color: green for bullish, red for bearish.

    Args:
        trend: Trend string ("bullish", "bearish", or other)

    Returns:
        Formatted colored trend string
    """
    if not trend:
        return "—"
    trend_lower = trend.lower()
    if trend_lower == "bullish":
        return f":green[{trend.title()}]"
    elif trend_lower == "bearish":
        return f":red[{trend.title()}]"
    else:
        return trend.title()


# Metric tooltips for user education
METRIC_TOOLTIPS = {
    "rsi": "Relative Strength Index (0-100): Measures momentum. >70 indicates overbought, <30 indicates oversold",
    "ema50": "50-day Exponential Moving Average: Short-term trend indicator",
    "ema200": "200-day Exponential Moving Average: Long-term trend indicator",
    "macd": "Moving Average Convergence Divergence: Momentum indicator showing relationship between two moving averages",
    "vol_21d": "21-day Realized Volatility: Annualized measure of price fluctuation",
    "vol_63d": "63-day Realized Volatility: Quarterly annualized price fluctuation",
    "dist_to_ema50": "Distance to EMA50: How far current price is from short-term trend line",
    "dist_to_ema200": "Distance to EMA200: How far current price is from long-term trend line",
    "peRatio": "Price-to-Earnings Ratio: Valuation metric comparing stock price to earnings per share",
    "marketCap": "Market Capitalization: Total value of all outstanding shares",
    "beta": "Beta: Volatility relative to market. >1 = more volatile than market, <1 = less volatile",
    "dividendYieldTTM": "Dividend Yield (TTM): Annual dividend payment as percentage of current stock price",
    "epsTTM": "Earnings Per Share (TTM): Trailing twelve months earnings divided by shares outstanding",
}


def _get_tooltip(metric_key: str) -> str:
    """Get tooltip description for a metric.

    Args:
        metric_key: Key for the metric (e.g., 'rsi', 'peRatio')

    Returns:
        Tooltip description or empty string if not found
    """
    return METRIC_TOOLTIPS.get(metric_key, "")


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


def _get_action_recommendation(technical: dict, fundamentals: dict) -> tuple[str, int, list[str]]:
    """Calculate Buy/Hold/Sell recommendation with confidence score.

    Args:
        technical: Technical analysis metrics
        fundamentals: Fundamental analysis metrics

    Returns:
        Tuple of (action, confidence, reasons)
    """
    score = 50  # Start neutral
    reasons: list[str] = []

    trend = ((technical or {}).get("trend") or "").lower()
    rsi = _safe_float((technical or {}).get("rsi"))
    macd_hist = _safe_float((technical or {}).get("macd_hist"))
    return_21d = _safe_float((technical or {}).get("return_21d"))
    return_63d = _safe_float((technical or {}).get("return_63d"))
    dist_to_ema50 = _safe_float((technical or {}).get("dist_to_ema50"))
    pe_ratio = _safe_float((fundamentals or {}).get("peRatio"))

    # Trend (±20)
    if trend == "bullish":
        score += 20
        reasons.append("📈 Bullish trend: EMA50 > EMA200")
    elif trend == "bearish":
        score -= 20
        reasons.append("📉 Bearish trend: EMA50 < EMA200")

    # RSI (±15)
    if rsi is not None:
        if rsi < 30:
            score += 15
            reasons.append(f"💎 RSI oversold ({rsi:.0f}): potential bounce opportunity")
        elif rsi > 70:
            score -= 15
            reasons.append(f"⚠️ RSI overbought ({rsi:.0f}): pullback risk")
        elif 40 <= rsi <= 60:
            score += 5
            reasons.append(f"✓ RSI neutral ({rsi:.0f}): balanced momentum")

    # MACD hist (±10)
    if macd_hist is not None:
        if macd_hist > 0:
            score += 10
            reasons.append("✓ MACD positive: upward momentum")
        elif macd_hist < -0.5:
            score -= 10
            reasons.append("⚠️ MACD negative: downward momentum")

    # Returns (±15)
    if return_21d is not None and return_63d is not None:
        if return_21d > 0.05 and return_63d > 0.10:
            score += 15
            reasons.append(f"🚀 Strong returns: 1M +{return_21d*100:.1f}%, 3M +{return_63d*100:.1f}%")
        elif return_21d < -0.05 and return_63d < -0.10:
            score -= 15
            reasons.append(f"⬇️ Weak returns: 1M {return_21d*100:.1f}%, 3M {return_63d*100:.1f}%")
    elif return_21d is not None:
        if return_21d > 0.05:
            score += 10
            reasons.append(f"📊 1-month gain: +{return_21d*100:.1f}%")
        elif return_21d < -0.05:
            score -= 10

    # Dist to EMA50 (±8)
    if dist_to_ema50 is not None:
        if dist_to_ema50 > 0.02:
            score += 8
        elif dist_to_ema50 < -0.05:
            score -= 8
            reasons.append(f"⚠️ Price {abs(dist_to_ema50)*100:.1f}% below EMA50")

    # P/E (±10)
    if pe_ratio is not None:
        if pe_ratio < 15:
            score += 10
            reasons.append(f"💰 Attractive valuation: P/E {pe_ratio:.1f}")
        elif pe_ratio > 40:
            score -= 10
            reasons.append(f"⚠️ High valuation: P/E {pe_ratio:.1f}")

    score = max(0, min(100, score))

    if score >= 65:
        action = "BUY"
        confidence = score
        if len(reasons) > 3:
            reasons = [
                r
                for r in reasons
                if any(token in r for token in ("📈", "💎", "✓", "🚀", "💰"))
            ][:3]
    elif score <= 35:
        action = "SELL"
        confidence = 100 - score
        if len(reasons) > 3:
            reasons = [r for r in reasons if any(token in r for token in ("📉", "⚠️", "⬇️"))][:3]
    else:
        action = "HOLD"
        confidence = 100 - abs(50 - score) * 2
        reasons = reasons[:3]

    if len(reasons) < 2:
        if action == "BUY":
            reasons.append("Multiple technical indicators suggest upside potential")
        elif action == "SELL":
            reasons.append("Multiple technical indicators suggest downside risk")
        else:
            reasons.append("Mixed signals suggest waiting for clearer trend")

    return action, confidence, reasons[:3]


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
col3.markdown(f"**Trend**  \n{_colored_trend(technical.get('trend'))}")
col4.metric("RSI (14)", f"{technical.get('rsi', float('nan')):.1f}" if technical.get("rsi") is not None else "—")

if _get_tooltip("rsi"):
    st.caption(f"💡 {_get_tooltip('rsi')}")

st.divider()

action, confidence, action_reasons = _get_action_recommendation(technical, fundamentals)

action_colors = {
    "BUY": "green",
    "HOLD": "orange",
    "SELL": "red",
}
action_emojis = {
    "BUY": "🚀",
    "HOLD": "⏸️",
    "SELL": "⚠️",
}

rec_col1, rec_col2 = st.columns([2, 3])
with rec_col1:
    color = action_colors.get(action, "gray")
    emoji = action_emojis.get(action, "")
    st.markdown(f"### {emoji} Recommendation")
    st.markdown(f"## :{color}[{action}]")
    st.markdown(f"**Confidence:** :{color}[{confidence}%]")
    st.caption("⚠️ Not financial advice. For informational purposes only.")

with rec_col2:
    st.markdown("### Key Factors")
    for reason in action_reasons:
        st.markdown(f"• {reason}")

st.divider()


# Prepare price data for charting
prices_payload = result.get("price_history") or []
prices = pd.DataFrame(prices_payload)
if not prices.empty and "date" in prices.columns:
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    prices = prices.dropna(subset=["date"]).sort_values("date").set_index("date")

if not prices.empty and "close" in prices.columns:
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices = prices.dropna(subset=["close"])


tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📊 Technical Analysis",
        "💼 Fundamental Analysis",
        "📈 Charts",
        "🤖 AI Insights",
        "📰 News & Catalysts",
    ]
)


with tab1:
    st.markdown("### Moving Averages & Trend")
    tcol1, tcol2, tcol3, tcol4 = st.columns(4)
    tcol1.metric("EMA 50", f"${technical.get('ema50', float('nan')):.2f}" if technical.get("ema50") is not None else "—")
    tcol2.metric("EMA 200", f"${technical.get('ema200', float('nan')):.2f}" if technical.get("ema200") is not None else "—")
    tcol3.markdown(f"**Trend**  \n{_colored_trend(technical.get('trend'))}")
    tcol4.metric("Last Close", f"${technical.get('close', float('nan')):.2f}" if technical.get("close") is not None else "—")
    if _get_tooltip("ema50"):
        st.caption(
            "💡 EMA 50/200 are exponential moving averages that smooth price trends. "
            "EMA50 > EMA200 suggests bullish momentum."
        )

    st.divider()

    st.markdown("### Momentum Indicators")
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("RSI (14)", f"{technical.get('rsi', float('nan')):.1f}" if technical.get("rsi") is not None else "—")
    mcol2.markdown(f"**RSI Band**  \n{(technical.get('rsi_band') or '—').title()}")
    mcol3.metric("Dist to EMA50", _fmt_signed_pct(technical.get("dist_to_ema50")))
    mcol4.metric("Dist to EMA200", _fmt_signed_pct(technical.get("dist_to_ema200")))
    if _get_tooltip("rsi"):
        st.caption(f"💡 {_get_tooltip('rsi')}")

    st.markdown("#### MACD")
    macd1, macd2, macd3 = st.columns(3)
    macd1.metric("MACD", _fmt_float(technical.get("macd"), decimals=3))
    macd2.metric("Signal", _fmt_float(technical.get("macd_signal"), decimals=3))
    macd3.metric("Histogram", _fmt_float(technical.get("macd_hist"), decimals=3))
    if _get_tooltip("macd"):
        st.caption(f"💡 {_get_tooltip('macd')}")

    st.divider()

    st.markdown("### Returns Analysis")
    rcol1, rcol2, rcol3, rcol4, rcol5 = st.columns(5)
    rcol1.markdown(f"**1W**  \n{_colored_pct(_safe_float(technical.get('return_5d')))}")
    rcol2.markdown(f"**1M**  \n{_colored_pct(_safe_float(technical.get('return_21d')))}")
    rcol3.markdown(f"**3M**  \n{_colored_pct(_safe_float(technical.get('return_63d')))}")
    rcol4.markdown(f"**YTD**  \n{_colored_pct(_safe_float(technical.get('return_ytd')))}")
    rcol5.markdown(
        f"**Max DD (1y)**  \n{_colored_pct(_safe_float(technical.get('max_drawdown_252d')), inverse=True)}"
    )
    st.caption(
        "💡 Green indicates positive returns, red indicates negative. Maximum drawdown shows largest peak-to-trough decline."
    )

    st.divider()

    st.markdown("### Volatility & Risk")
    vcol1, vcol2, vcol3, vcol4 = st.columns(4)
    vcol1.metric("Vol (21d)", _pct(technical.get("vol_21d")))
    vcol2.metric("Vol (63d)", _pct(technical.get("vol_63d")))
    vcol3.metric("52W High", f"${technical.get('52w_high', float('nan')):.2f}" if technical.get("52w_high") is not None else "—")
    vcol4.metric("52W Low", f"${technical.get('52w_low', float('nan')):.2f}" if technical.get("52w_low") is not None else "—")
    if _get_tooltip("vol_21d"):
        st.caption(f"💡 {_get_tooltip('vol_21d')}")

    with st.expander("📋 Technical Details (All Metrics)"):
        if technical:
            _tech_df = pd.DataFrame([{"Metric": k, "Value": v} for k, v in technical.items()]).astype(str)
            _df(_tech_df, hide_index=True)
        else:
            st.write("No technical summary available.")


with tab2:
    st.markdown("### Company Overview")
    comp_col1, comp_col2, comp_col3 = st.columns(3)
    comp_col1.metric("Company", fundamentals.get("companyName") or "—")
    comp_col2.metric("Sector", fundamentals.get("sector") or "—")
    comp_col3.metric("Industry", fundamentals.get("industry") or "—")

    st.divider()

    st.markdown("### Valuation Metrics")
    val_col1, val_col2, val_col3 = st.columns(3)
    val_col1.metric("Market Cap", _fmt_money(fundamentals.get("marketCap")))
    val_col2.metric("P/E Ratio (TTM)", str(fundamentals.get("peRatio") or "—"))
    val_col3.metric("EPS (TTM)", _fmt_float(fundamentals.get("epsTTM"), decimals=2))
    if _get_tooltip("peRatio"):
        st.caption(f"💡 {_get_tooltip('peRatio')}")

    st.divider()

    st.markdown("### Dividend & Risk")
    div_col1, div_col2 = st.columns(2)
    div_col1.metric("Dividend Yield (TTM)", _pct(_safe_float(fundamentals.get("dividendYieldTTM"))))
    beta_val = _safe_float(fundamentals.get("beta"))
    if beta_val is not None:
        beta_color = "red" if beta_val > 1 else "green"
        div_col2.markdown(f"**Beta**  \n:{beta_color}[{beta_val:.2f}]")
    else:
        div_col2.metric("Beta", "—")
    if _get_tooltip("beta"):
        st.caption(f"💡 {_get_tooltip('beta')}")

    st.divider()

    st.markdown("### 52-Week Range")
    high_52w = _safe_float(fundamentals.get("52WeekHigh"))
    low_52w = _safe_float(fundamentals.get("52WeekLow"))
    current_close = _safe_float(technical.get("close"))
    if high_52w is not None and low_52w is not None and current_close is not None:
        denom = (high_52w - low_52w)
        range_pct = (current_close - low_52w) / denom if denom != 0 else 0.5
        st.progress(range_pct)
        st.caption(f"Low: ${low_52w:.2f} | Current: ${current_close:.2f} | High: ${high_52w:.2f}")
    else:
        st.caption(
            "52W Range: "
            + (f"${low_52w:.2f}" if low_52w is not None else "—")
            + " – "
            + (f"${high_52w:.2f}" if high_52w is not None else "—")
        )

    with st.expander("📋 Fundamental Details (All Metrics)"):
        if fundamentals:
            _fund_df = pd.DataFrame([{"Field": k, "Value": v} for k, v in fundamentals.items()]).astype(str)
            _df(_fund_df, hide_index=True)
        else:
            st.write("No fundamentals summary available.")


with tab3:
    if not prices.empty:
        st.markdown("### Price Performance")
        perf_col1, perf_col2, perf_col3, perf_col4, perf_col5 = st.columns(5)
        perf_col1.markdown(f"**1W**  \n{_colored_pct(_safe_float(technical.get('return_5d')))}")
        perf_col2.markdown(f"**1M**  \n{_colored_pct(_safe_float(technical.get('return_21d')))}")
        perf_col3.markdown(f"**3M**  \n{_colored_pct(_safe_float(technical.get('return_63d')))}")
        perf_col4.markdown(f"**YTD**  \n{_colored_pct(_safe_float(technical.get('return_ytd')))}")
        perf_col5.markdown(
            f"**Max DD (1y)**  \n{_colored_pct(_safe_float(technical.get('max_drawdown_252d')), inverse=True)}"
        )

        st.divider()

        st.markdown("### Price Chart with Moving Averages")
        ema50_series = prices["close"].ewm(span=50, adjust=False).mean()
        ema200_series = prices["close"].ewm(span=200, adjust=False).mean()
        chart_df = pd.DataFrame({"Close": prices["close"], "EMA50": ema50_series, "EMA200": ema200_series})
        st.line_chart(chart_df, height=400)
        st.caption("💡 Chart shows closing price (blue), 50-day EMA (orange), and 200-day EMA (green)")

        with st.expander("📊 Recent Price Data"):
            _df(prices.tail(30))
    else:
        st.info("No price history available for charting.")


with tab4:
    st.markdown("### AI-Powered Analysis")
    llm_md = result.get("llm_analysis") or ""
    if llm_md:
        st.markdown(llm_md)
    else:
        st.info("LLM analysis unavailable.")

    st.divider()

    st.markdown("### Investment Recommendations")
    short_rec, long_rec, rec_reasons = _recommendations(technical, fundamentals)

    def _color_recommendation(rec: str) -> str:
        rec_lower = rec.lower()
        if any(word in rec_lower for word in ["bullish", "constructive", "opportunistic"]):
            return f":green[{rec}]"
        elif any(word in rec_lower for word in ["bearish", "cautious"]):
            return f":red[{rec}]"
        else:
            return rec

    rec1, rec2 = st.columns(2)
    rec1.markdown(f"**Short-term (days–weeks)**  \n{_color_recommendation(short_rec)}")
    rec2.markdown(f"**Long-term (months+)**  \n{_color_recommendation(long_rec)}")
    with st.expander("ℹ️ Why these recommendations?"):
        for reason in rec_reasons:
            st.write(f"- {reason}")


with tab5:
    llm_md = result.get("llm_analysis") or ""
    st.markdown("### Catalysts & Key Risks")
    cat_col1, cat_col2 = st.columns(2)
    with cat_col1:
        st.markdown("**📅 Upcoming Catalysts**")
        if event_highlights:
            for ev in event_highlights[:5]:
                st.write(f"• {ev.get('date') or '—'} (EPS est: {ev.get('epsEstimated') or '—'})")
        elif news_highlights:
            for item in news_highlights[:5]:
                title = item.get("headline") or "(headline unavailable)"
                url = item.get("url")
                if url:
                    st.markdown(f"• [{title}]({url})")
                else:
                    st.write(f"• {title}")
        else:
            st.write("• No upcoming catalysts identified")

    with cat_col2:
        st.markdown("**⚠️ Key Risks**")
        risks = _extract_markdown_section(llm_md, "Key Risks")
        if risks:
            st.markdown(risks)
        else:
            st.write("• No specific risks identified")

    st.divider()

    st.markdown("### Recent News (7 days)")
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
        st.info("No recent news items available.")

    with st.expander("🔍 Raw Data (Debug)"):
        st.markdown("**Context**")
        st.json(context)
        st.markdown("**News (raw)**")
        st.write(raw_news)
        st.markdown("**Events (raw)**")
        st.write(result.get("raw_events") or [])


st.caption("For informational purposes only. Not financial advice.")
