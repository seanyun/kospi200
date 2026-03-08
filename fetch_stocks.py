#!/usr/bin/env python3
"""Fetch KOSPI 200 top 10 stock data and output as JSON."""
import json
import sys
import warnings
warnings.filterwarnings('ignore')

import yfinance as yf

TOP10 = [
    {"ticker": "005930.KS", "name": "삼성전자",     "nameEn": "Samsung Electronics",    "sector": "Technology"},
    {"ticker": "000660.KS", "name": "SK하이닉스",   "nameEn": "SK Hynix",               "sector": "Technology"},
    {"ticker": "373220.KS", "name": "LG에너지솔루션","nameEn": "LG Energy Solution",     "sector": "Energy"},
    {"ticker": "005380.KS", "name": "현대차",        "nameEn": "Hyundai Motor",          "sector": "Automotive"},
    {"ticker": "207940.KS", "name": "삼성바이오로직스","nameEn": "Samsung Biologics",    "sector": "Healthcare"},
    {"ticker": "005490.KS", "name": "POSCO홀딩스",   "nameEn": "POSCO Holdings",         "sector": "Materials"},
    {"ticker": "068270.KS", "name": "셀트리온",      "nameEn": "Celltrion",              "sector": "Healthcare"},
    {"ticker": "105560.KS", "name": "KB금융",        "nameEn": "KB Financial Group",     "sector": "Financials"},
    {"ticker": "055550.KS", "name": "신한지주",      "nameEn": "Shinhan Financial Group","sector": "Financials"},
    {"ticker": "035420.KS", "name": "NAVER",         "nameEn": "NAVER",                  "sector": "Technology"},
]

def safe(val):
    """Convert numpy types to plain Python types."""
    try:
        if val is None:
            return None
        f = float(val)
        return None if (f != f) else f  # NaN check
    except Exception:
        return None

def fetch_one(meta):
    try:
        t = yf.Ticker(meta["ticker"])
        fi = t.fast_info
        price    = safe(fi.last_price)
        prev     = safe(fi.previous_close)
        mktcap   = safe(fi.market_cap)
        change     = round(price - prev, 2) if price is not None and prev is not None else None
        change_pct = round((price - prev) / prev * 100, 2) if price and prev else None
        return {**meta, "price": price, "prevClose": prev, "change": change,
                "changePct": change_pct, "marketCap": mktcap, "currency": "KRW"}
    except Exception as e:
        return {**meta, "price": None, "prevClose": None, "change": None,
                "changePct": None, "marketCap": None, "currency": "KRW", "error": str(e)}

def main():
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(fetch_one, TOP10))

    results.sort(key=lambda s: s["marketCap"] or 0, reverse=True)

    print(json.dumps({"stocks": results}))

if __name__ == "__main__":
    main()
