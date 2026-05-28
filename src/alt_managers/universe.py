"""universe.py — The tracked universe of listed alternative asset managers."""

TICKERS = {
    # Big Seven — US diversified
    "BX":      {"name": "Blackstone",           "category": "Big Seven",  "geo": "US",     "tilt": "Diversified",              "ccy": "USD"},
    "KKR":     {"name": "KKR",                   "category": "Big Seven",  "geo": "US",     "tilt": "Diversified",              "ccy": "USD"},
    "APO":     {"name": "Apollo",                "category": "Big Seven",  "geo": "US",     "tilt": "Credit/Insurance",         "ccy": "USD"},
    "CG":      {"name": "Carlyle",               "category": "Big Seven",  "geo": "US",     "tilt": "PE-led",                   "ccy": "USD"},
    "BAM":     {"name": "Brookfield Asset Mgmt", "category": "Big Seven",  "geo": "Canada", "tilt": "Real assets (pure-play)",  "ccy": "USD"},
    "TPG":     {"name": "TPG",                   "category": "Big Seven+", "geo": "US",     "tilt": "PE/Growth/Impact",         "ccy": "USD"},
    # European
    "EQT.ST":  {"name": "EQT AB",                "category": "European",   "geo": "Europe", "tilt": "PE/Infrastructure",        "ccy": "SEK"},
    "CVC.AS":  {"name": "CVC Capital",           "category": "European",   "geo": "Europe", "tilt": "PE mega-buyout",           "ccy": "EUR"},
    "PGHN.SW": {"name": "Partners Group",        "category": "European",   "geo": "Europe", "tilt": "Diversified/Secondaries", "ccy": "CHF"},
}

CATEGORIES = ["Big Seven", "Big Seven+", "European"]
GEOS = ["US", "Canada", "Europe"]
TILTS = sorted({v["tilt"] for v in TICKERS.values()})
