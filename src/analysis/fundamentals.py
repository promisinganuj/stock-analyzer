def fundamentals_summary(fundamentals_payload: dict):
    if not fundamentals_payload:
        return {}

    # Back-compat: older code may pass the raw FMP profile list/dict.
    if isinstance(fundamentals_payload, (list, dict)) and not (
        isinstance(fundamentals_payload, dict)
        and ("fmp_profile" in fundamentals_payload or "finnhub_metrics" in fundamentals_payload)
    ):
        fmp_profile_json = fundamentals_payload
        finnhub_metrics = None
    else:
        fmp_profile_json = (fundamentals_payload or {}).get("fmp_profile")
        finnhub_metrics = (fundamentals_payload or {}).get("finnhub_metrics")

    # FinancialModelingPrep profile returns list with one object
    profile = (
        fmp_profile_json[0]
        if isinstance(fmp_profile_json, list) and fmp_profile_json
        else (fmp_profile_json or {})
    )

    metrics = {}
    if isinstance(finnhub_metrics, dict):
        metrics = finnhub_metrics.get("metric") or {}

    pe_ratio = (
        profile.get("pe")
        or profile.get("peRatio")
        or profile.get("priceEarningsRatio")
        or metrics.get("peTTM")
        or metrics.get("peBasicExclExtraTTM")
        or metrics.get("peInclExtraTTM")
    )

    market_cap = (
        profile.get("mktCap")
        or profile.get("marketCap")
        or metrics.get("marketCapitalization")
    )

    summary = {
        "companyName": profile.get("companyName") or profile.get("company"),
        "sector": profile.get("sector"),
        "industry": profile.get("industry"),
        "marketCap": market_cap,
        "peRatio": pe_ratio,
        "beta": profile.get("beta") or metrics.get("beta"),
        # A few helpful extras (may be None depending on provider/data)
        "epsTTM": metrics.get("epsTTM"),
        "dividendYieldTTM": metrics.get("dividendYieldIndicatedAnnual"),
        "52WeekHigh": metrics.get("52WeekHigh"),
        "52WeekLow": metrics.get("52WeekLow"),
    }
    return summary
