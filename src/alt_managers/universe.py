"""universe.py — The tracked universe of listed alternative asset managers."""

TICKERS = {
    # Big Seven — US diversified
    "BX":      {"name": "Blackstone",           "category": "Big Seven",  "geo": "US",     "tilt": "Diversified",              "ccy": "USD"},
    "KKR":     {"name": "KKR",                   "category": "Big Seven",  "geo": "US",     "tilt": "Diversified",              "ccy": "USD"},
    "APO":     {"name": "Apollo",                "category": "Big Seven",  "geo": "US",     "tilt": "Credit/Insurance",         "ccy": "USD"},
    "ARES":    {"name": "Ares",                  "category": "Big Seven",  "geo": "US",     "tilt": "Credit-led",               "ccy": "USD"},
    "CG":      {"name": "Carlyle",               "category": "Big Seven",  "geo": "US",     "tilt": "PE-led",                   "ccy": "USD"},
    "OWL":     {"name": "Blue Owl",              "category": "Big Seven",  "geo": "US",     "tilt": "GP stakes/Credit",         "ccy": "USD"},
    "BN":      {"name": "Brookfield Corp",       "category": "Big Seven",  "geo": "Canada", "tilt": "Real assets + bal sheet",  "ccy": "USD"},
    "BAM":     {"name": "Brookfield Asset Mgmt", "category": "Big Seven",  "geo": "Canada", "tilt": "Real assets (pure-play)",  "ccy": "USD"},
    "TPG":     {"name": "TPG",                   "category": "Big Seven+", "geo": "US",     "tilt": "PE/Growth/Impact",         "ccy": "USD"},
    # European
    "EQT.ST":  {"name": "EQT AB",                "category": "European",   "geo": "Europe", "tilt": "PE/Infrastructure",        "ccy": "SEK"},
    "CVC.AS":  {"name": "CVC Capital",           "category": "European",   "geo": "Europe", "tilt": "PE mega-buyout",           "ccy": "EUR"},
    "III.L":   {"name": "3i Group",              "category": "European",   "geo": "Europe", "tilt": "Mid-market PE/Infra",      "ccy": "GBP"},
    "BPT.L":   {"name": "Bridgepoint",           "category": "European",   "geo": "Europe", "tilt": "Mid-market PE",            "ccy": "GBP"},
    "PGHN.SW": {"name": "Partners Group",        "category": "European",   "geo": "Europe", "tilt": "Diversified/Secondaries", "ccy": "CHF"},
    # Specialists
    "HLNE":    {"name": "Hamilton Lane",         "category": "Specialist", "geo": "US",     "tilt": "Secondaries/FoF",          "ccy": "USD"},
    "STEP":    {"name": "StepStone",             "category": "Specialist", "geo": "US",     "tilt": "Secondaries/FoF",          "ccy": "USD"},
    "PAX":     {"name": "Patria",                "category": "Specialist", "geo": "LatAm",  "tilt": "LatAm alts",               "ccy": "USD"},
    "PJT":     {"name": "PJT Partners",          "category": "Specialist", "geo": "US",     "tilt": "Advisory-led",             "ccy": "USD"},
    "EMG.L":   {"name": "Man Group",             "category": "Specialist", "geo": "Europe", "tilt": "Hedge funds",              "ccy": "GBP"},
}

CATEGORIES = ["Big Seven", "Big Seven+", "European", "Specialist"]
GEOS = ["US", "Canada", "Europe", "LatAm"]
TILTS = sorted({v["tilt"] for v in TICKERS.values()})
