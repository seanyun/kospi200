#!/usr/bin/env python3
"""Fetch 30-day daily OHLCV history for a ticker and output as JSON."""
import json
import sys
import warnings
warnings.filterwarnings('ignore')

import yfinance as yf

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No ticker provided"}))
        sys.exit(1)

    ticker = sys.argv[1]
    df = yf.download(ticker, period='35d', interval='1d', auto_adjust=True, progress=False)

    if df.empty:
        print(json.dumps({"error": "No data"}))
        sys.exit(1)

    # Keep last 30 trading days
    df = df.tail(30)

    bars = []
    for date, row in df.iterrows():
        bars.append({
            "time":  date.strftime('%Y-%m-%d'),
            "open":  round(float(row['Open']),  2),
            "high":  round(float(row['High']),  2),
            "low":   round(float(row['Low']),   2),
            "close": round(float(row['Close']), 2),
        })

    print(json.dumps({"ticker": ticker, "bars": bars}))

if __name__ == "__main__":
    main()
