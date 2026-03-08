#!/usr/bin/env python3
"""Fetch market data for a broad pool of KOSPI 200 candidates and output as JSON."""
import json
import warnings
warnings.filterwarnings('ignore')

import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

# ~30 major KOSPI 200 components across sectors
CANDIDATES = [
    {"ticker": "005930.KS", "name": "삼성전자",       "nameEn": "Samsung Electronics",      "sector": "Technology"},
    {"ticker": "000660.KS", "name": "SK하이닉스",     "nameEn": "SK Hynix",                 "sector": "Technology"},
    {"ticker": "373220.KS", "name": "LG에너지솔루션", "nameEn": "LG Energy Solution",        "sector": "Energy"},
    {"ticker": "005380.KS", "name": "현대차",          "nameEn": "Hyundai Motor",             "sector": "Automotive"},
    {"ticker": "207940.KS", "name": "삼성바이오로직스","nameEn": "Samsung Biologics",         "sector": "Healthcare"},
    {"ticker": "005490.KS", "name": "POSCO홀딩스",    "nameEn": "POSCO Holdings",            "sector": "Materials"},
    {"ticker": "068270.KS", "name": "셀트리온",        "nameEn": "Celltrion",                 "sector": "Healthcare"},
    {"ticker": "105560.KS", "name": "KB금융",          "nameEn": "KB Financial Group",        "sector": "Financials"},
    {"ticker": "055550.KS", "name": "신한지주",        "nameEn": "Shinhan Financial Group",   "sector": "Financials"},
    {"ticker": "035420.KS", "name": "NAVER",           "nameEn": "NAVER",                     "sector": "Technology"},
    {"ticker": "000270.KS", "name": "기아",            "nameEn": "Kia",                       "sector": "Automotive"},
    {"ticker": "051910.KS", "name": "LG화학",          "nameEn": "LG Chem",                   "sector": "Materials"},
    {"ticker": "035720.KS", "name": "카카오",          "nameEn": "Kakao",                     "sector": "Technology"},
    {"ticker": "006400.KS", "name": "삼성SDI",         "nameEn": "Samsung SDI",               "sector": "Energy"},
    {"ticker": "028260.KS", "name": "삼성물산",        "nameEn": "Samsung C&T",               "sector": "Conglomerate"},
    {"ticker": "066570.KS", "name": "LG전자",          "nameEn": "LG Electronics",            "sector": "Technology"},
    {"ticker": "003550.KS", "name": "LG",              "nameEn": "LG Corp",                   "sector": "Conglomerate"},
    {"ticker": "034730.KS", "name": "SK",              "nameEn": "SK Inc",                    "sector": "Conglomerate"},
    {"ticker": "017670.KS", "name": "SK텔레콤",        "nameEn": "SK Telecom",                "sector": "Telecom"},
    {"ticker": "030200.KS", "name": "KT",              "nameEn": "KT Corp",                   "sector": "Telecom"},
    {"ticker": "015760.KS", "name": "한국전력",        "nameEn": "KEPCO",                     "sector": "Utilities"},
    {"ticker": "086790.KS", "name": "하나금융지주",    "nameEn": "Hana Financial Group",      "sector": "Financials"},
    {"ticker": "316140.KS", "name": "우리금융지주",    "nameEn": "Woori Financial Group",     "sector": "Financials"},
    {"ticker": "096770.KS", "name": "SK이노베이션",    "nameEn": "SK Innovation",             "sector": "Energy"},
    {"ticker": "010950.KS", "name": "S-Oil",           "nameEn": "S-Oil",                     "sector": "Energy"},
    {"ticker": "011170.KS", "name": "롯데케미칼",      "nameEn": "Lotte Chemical",            "sector": "Materials"},
    {"ticker": "003490.KS", "name": "대한항공",        "nameEn": "Korean Air",                "sector": "Transportation"},
    {"ticker": "000810.KS", "name": "삼성화재",        "nameEn": "Samsung Fire & Marine",     "sector": "Insurance"},
    {"ticker": "033780.KS", "name": "KT&G",            "nameEn": "KT&G",                      "sector": "Consumer"},
    {"ticker": "009150.KS", "name": "삼성전기",        "nameEn": "Samsung Electro-Mechanics", "sector": "Technology"},
]

def safe(val):
    try:
        if val is None: return None
        f = float(val)
        return None if (f != f) else f
    except Exception:
        return None

def fetch_one(meta):
    try:
        t = yf.Ticker(meta["ticker"])
        fi = t.fast_info
        price    = safe(fi.last_price)
        prev     = safe(fi.previous_close)
        mktcap   = safe(fi.market_cap)
        change_pct = round((price - prev) / prev * 100, 2) if price and prev else None
        return {
            **meta,
            "price":     price,
            "prevClose": prev,
            "change":    round(price - prev, 2) if price is not None and prev is not None else None,
            "changePct": change_pct,
            "marketCap": mktcap,
            "currency":  "KRW",
        }
    except Exception as e:
        return {**meta, "price": None, "prevClose": None, "change": None,
                "changePct": None, "marketCap": None, "currency": "KRW", "error": str(e)}

def main():
    with ThreadPoolExecutor(max_workers=15) as pool:
        results = list(pool.map(fetch_one, CANDIDATES))
    # Filter out stocks with no price data
    results = [r for r in results if r.get("price") is not None]
    print(json.dumps({"candidates": results}))

if __name__ == "__main__":
    main()
