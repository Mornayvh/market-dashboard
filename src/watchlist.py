"""
watchlist.py — The stock watchlist universe.

Single source of truth for the tracked holdings, shared by the Streamlit page
(pages/3_Stock_Watchlist.py) and the PDF exporter (export_watchlist_pdf.py).
Both used to carry their own copy of this dict; add or remove names here only.

Entries are (display name, Yahoo Finance ticker, listing currency). Group order
is the display order on both surfaces, and the order within a group is the row
order, so keep each group alphabetical unless there is a reason not to.
"""

WATCHLIST: dict[str, list[tuple[str, str, str]]] = {
    "Core Holdings": [
        ("Richemont", "CFR.SW", "CHF"),
        ("Remgro", "REM.JO", "ZAR"),
        ("Reinet", "REINA.AS", "EUR"),
    ],
    "Connected Holdings": [
        ("BAT (LSE)", "BATS.L", "GBP"),
        ("BAT (JSE)", "BTI.JO", "ZAR"),
        ("FirstRand", "FSR.JO", "ZAR"),
        ("OUTsurance", "OUT.JO", "ZAR"),
        ("Discovery", "DSY.JO", "ZAR"),
    ],
    "Tiger Global IPO's": [
        ("Cerebras", "CBRS", "USD"),
    ],
    "USA Tech": [
        ("Alphabet", "GOOGL", "USD"),
        ("Amazon", "AMZN", "USD"),
        ("Apple", "AAPL", "USD"),
        ("Dell", "DELL", "USD"),
        ("Meta", "META", "USD"),
        ("Microsoft", "MSFT", "USD"),
        ("Nvidia", "NVDA", "USD"),
        ("SpaceX", "SPCX", "USD"),
        ("Tesla", "TSLA", "USD"),
        ("Palo Alto", "PANW", "USD"),
        ("Uber", "UBER", "USD"),
    ],
    "China Tech": [
        ("Alibaba", "BABA", "USD"),
        ("BYD", "002594.SZ", "CNY"),
        ("CXMT", "688825.SS", "CNY"),
        ("Tencent", "TCEHY", "USD"),
        ("Unitree", "688836.SS", "CNY"),
    ],
    "Financials": [
        ("JP Morgan", "JPM", "USD"),
        ("Goldman Sachs", "GS", "USD"),
        ("BofA", "BAC", "USD"),
        ("Morgan Stanley", "MS", "USD"),
        ("Berkshire Hathaway", "BRK-B", "USD"),
        ("Markel", "MKL", "USD"),
        ("Apollo", "APO", "USD"),
        ("KKR", "KKR", "USD"),
    ],
    "Real World": [
        ("Deere & Co", "DE", "USD"),
        ("Teledyne", "TDY", "USD"),
        ("Waste Management", "WM", "USD"),
    ],
}

CURRENCY_SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€", "CHF": "CHF ", "ZAR": "R", "CNY": "¥"}

# Calendar-day span a 1y fetch must cover before LTM and 52-week figures are
# reported. Below this the series is a recent listing, not a year of trading.
# 300 rather than 365 so exchange holidays and short weeks don't trip it.
FULL_YEAR_MIN_DAYS = 300
