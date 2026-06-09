"""
refresh_fundamentals.py
Weekly SEC EDGAR fundamentals refresh — run by GitHub Actions (Saturday cron).
Pulls 10-K company facts for the configured AI/mega-cap cohort into
data/fundamentals.db; the workflow then commits the DB so Streamlit Cloud
redeploys with fresh data (powers pages/6_Fundamentals.py and 7_AI_Capex.py).

Reads SEC_USER_AGENT from the environment (set in the workflow).
"""

from src import fundamentals_process as fp
from src.config import FUNDAMENTALS_TICKERS


def main():
    result = fp.refresh_all(tickers=FUNDAMENTALS_TICKERS)
    print(f"Refreshed {result['total_rows']} rows for {FUNDAMENTALS_TICKERS}")
    for ticker, coverage in result["per_ticker"].items():
        print(f"  {ticker}: {coverage}")


if __name__ == "__main__":
    main()
