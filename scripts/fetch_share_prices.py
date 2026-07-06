"""
fetch_share_prices.py
Pull daily share-price history from Yahoo Finance (yfinance) for the mega-cap AI
cohort and write one sheet per company into a single Excel workbook.

Each sheet holds the full available daily history: Date, Open, High, Low, Close,
Adj Close, Volume. `auto_adjust=False` keeps the raw OHLC alongside the split/
dividend-adjusted "Adj Close".

Usage:  .venv/bin/python scripts/fetch_share_prices.py [--period max] [--out PATH]
"""

import argparse
import sys

import pandas as pd
import yfinance as yf

# Company name (as requested) -> Yahoo ticker. Sheet names use the company name.
COMPANIES = {
    "NVIDIA": "NVDA",
    "META": "META",
    "APPLE": "AAPL",
    "MICROSOFT": "MSFT",
    "ALPHABET": "GOOGL",
    "AMAZON": "AMZN",
}

COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]


def fetch(ticker: str, period: str) -> pd.DataFrame:
    """Daily OHLCV + Adj Close for one ticker, oldest first, Date as a column."""
    df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame(columns=["Date"] + COLUMNS)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df[[c for c in COLUMNS if c in df.columns]].copy()
    if "Close" in df.columns:
        df = df.dropna(subset=["Close"])  # drop incomplete/provisional sessions
    df.insert(0, "Date", df.index.date)
    return df.reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default="max",
                    help="yfinance period (e.g. max, 10y, 5y). Default: max.")
    ap.add_argument("--out", default="share_prices_daily.xlsx",
                    help="Output .xlsx path. Default: share_prices_daily.xlsx")
    args = ap.parse_args()

    with pd.ExcelWriter(args.out, engine="openpyxl", datetime_format="yyyy-mm-dd") as xl:
        for name, ticker in COMPANIES.items():
            df = fetch(ticker, args.period)
            df.to_excel(xl, sheet_name=name, index=False)
            span = (f"{df['Date'].iloc[0]} → {df['Date'].iloc[-1]}"
                    if not df.empty else "no data")
            print(f"  {name:10} ({ticker:5}) {len(df):>6} rows   {span}")

    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
