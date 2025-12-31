import pandas as pd
import numpy as np

def compute_ema(series: pd.Series, span: int):
    return series.ewm(span=span, adjust=False).mean()

def compute_rsi(series: pd.Series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=period-1, adjust=False).mean()
    ma_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))


def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = compute_ema(series, fast)
    ema_slow = compute_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _pct_change_over(series: pd.Series, periods: int):
    if series is None or series.empty:
        return None
    if len(series) <= periods:
        return None
    start = series.iloc[-(periods + 1)]
    end = series.iloc[-1]
    if start == 0 or pd.isna(start) or pd.isna(end):
        return None
    return float(end / start - 1)


def _realized_vol(returns: pd.Series, window: int):
    if returns is None or returns.empty or len(returns.dropna()) < window:
        return None
    # annualize using 252 trading days
    return float(returns.dropna().tail(window).std() * np.sqrt(252))


def _max_drawdown(series: pd.Series, window: int | None = None):
    if series is None or series.empty:
        return None
    s = series.dropna()
    if window is not None and len(s) > window:
        s = s.tail(window)
    if s.empty:
        return None
    running_max = s.cummax()
    dd = s / running_max - 1.0
    return float(dd.min())


def _ytd_return(series: pd.Series):
    if series is None or series.empty:
        return None
    s = series.dropna()
    if s.empty:
        return None
    idx = s.index
    if not isinstance(idx, pd.DatetimeIndex):
        return None
    start_of_year = pd.Timestamp(year=idx[-1].year, month=1, day=1, tz=idx.tz)
    s_ytd = s[s.index >= start_of_year]
    if len(s_ytd) < 2:
        return None
    start = s_ytd.iloc[0]
    end = s_ytd.iloc[-1]
    if start == 0 or pd.isna(start) or pd.isna(end):
        return None
    return float(end / start - 1)

def technical_summary(df: pd.DataFrame):
    if df.empty:
        return {}
    if "close" not in df.columns:
        return {}
    s = df["close"].dropna()
    if s.empty:
        return {}

    latest_close = s.iloc[-1]
    ema50 = compute_ema(s, 50).iloc[-1] if len(s) >= 50 else compute_ema(s, int(len(s)/2)).iloc[-1]
    ema200 = compute_ema(s, 200).iloc[-1] if len(s) >= 200 else compute_ema(s, int(len(s)*0.8)).iloc[-1]
    rsi = compute_rsi(s).iloc[-1]
    trend = "bullish" if ema50 > ema200 else "bearish"

    returns = s.pct_change()
    macd_line, signal_line, hist = compute_macd(s)

    r_5d = _pct_change_over(s, 5)
    r_21d = _pct_change_over(s, 21)
    r_63d = _pct_change_over(s, 63)
    r_252d = _pct_change_over(s, 252)
    r_ytd = _ytd_return(s)

    vol_21d = _realized_vol(returns, 21)
    vol_63d = _realized_vol(returns, 63)
    mdd_252d = _max_drawdown(s, 252)

    w52_window = 252 if len(s) >= 252 else len(s)
    w52_high = float(s.tail(w52_window).max()) if w52_window else None
    w52_low = float(s.tail(w52_window).min()) if w52_window else None

    dist_ema50 = float(latest_close / ema50 - 1) if ema50 else None
    dist_ema200 = float(latest_close / ema200 - 1) if ema200 else None

    rsi_band = "neutral"
    if float(rsi) >= 70:
        rsi_band = "overbought"
    elif float(rsi) <= 30:
        rsi_band = "oversold"

    return {
        "close": float(latest_close),
        "ema50": float(ema50),
        "ema200": float(ema200),
        "rsi": float(rsi),
        "trend": trend,
        "rsi_band": rsi_band,
        "dist_to_ema50": dist_ema50,
        "dist_to_ema200": dist_ema200,
        "return_5d": r_5d,
        "return_21d": r_21d,
        "return_63d": r_63d,
        "return_252d": r_252d,
        "return_ytd": r_ytd,
        "vol_21d": vol_21d,
        "vol_63d": vol_63d,
        "max_drawdown_252d": mdd_252d,
        "52w_high": w52_high,
        "52w_low": w52_low,
        "macd": float(macd_line.iloc[-1]) if not macd_line.empty else None,
        "macd_signal": float(signal_line.iloc[-1]) if not signal_line.empty else None,
        "macd_hist": float(hist.iloc[-1]) if not hist.empty else None,
    }
