"""
config.py — Direct Investments configuration.
Per-holding tickers, ETF candidates, FRED IDs, Google Trends queries,
and static-data file references. Single source of truth.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Comp:
    name: str
    ticker: str
    is_primary: bool = False


@dataclass(frozen=True)
class Sparkline:
    name: str
    ticker: str
    caption: str = ""


@dataclass(frozen=True)
class FredSeries:
    name: str
    series_id: str
    unit_suffix: str = ""          # "%", "bps", etc.
    invert_color: bool = False     # True when "up = bad"


@dataclass(frozen=True)
class TrendsQuery:
    label: str
    keywords: tuple                  # passed to pytrends as keyword list
    geo: str = "US"
    timeframe: str = "today 12-m"


@dataclass(frozen=True)
class StaticBlock:
    """A static data section sourced from a hand-edited YAML."""
    title: str
    yaml_file: str
    chart_kind: str                 # "grouped_bar" | "line" | "bar"
    caption: str = ""


@dataclass(frozen=True)
class Holding:
    key: str                         # url-safe slug
    name: str                        # display name
    description: str                 # one-liner
    thesis: str                      # what's working
    risk: str                        # what to watch
    comps: tuple                     # tuple[Comp]
    sparklines: tuple                # tuple[Sparkline] — sector ETFs
    commodities: tuple = ()          # tuple[Sparkline]
    fred_series: tuple = ()          # tuple[FredSeries]
    extra_tickers: tuple = ()        # tuple[Sparkline] for industry/sentiment YF series (XBI etc.)
    trends_queries: tuple = ()       # tuple[TrendsQuery]
    static_blocks: tuple = ()        # tuple[StaticBlock]
    static_caption: Optional[str] = None


# ---------------------------------------------------------------------------
# ETF liquidity helper — used at runtime to pick the most liquid pharma ETF
# from a candidate list. Kept here so the choice is reviewable.
# ---------------------------------------------------------------------------

PHARMA_ETF_CANDIDATES = ("XLV", "IHE", "XPH")  # broad health, US pharma, S&P pharma
HEALTH_INSURER_ETF = "IHF"                       # standard liquid name, no choice needed


# ---------------------------------------------------------------------------
# Novolex — packaging
# ---------------------------------------------------------------------------

NOVOLEX = Holding(
    key="novolex",
    name="Novolex",
    description="Diversified packaging (food service, flexible & rigid) post-Pactiv merger.",
    thesis="CPG and food-service demand recovery; integration of Pactiv assets driving margin expansion.",
    risk="Resin/oil input cost volatility; restaurant traffic softness; freight inflation.",
    comps=(
        Comp("Amcor",            "AMCR", is_primary=True),
        Comp("Sealed Air",       "SEE"),
        Comp("Huhtamaki",        "HUH1V.HE"),
        Comp("Graphic Packaging","GPK"),
        Comp("Sonoco",           "SON"),
    ),
    sparklines=(
        Sparkline("Consumer Discretionary", "XLY", "Restaurant / dining proxy"),
        Sparkline("Consumer Staples",       "XLP", "CPG demand proxy"),
    ),
    commodities=(
        Sparkline("Brent",       "BZ=F",  "Resin feedstock proxy"),
        Sparkline("WTI",         "CL=F",  "Resin feedstock proxy"),
        Sparkline("Henry Hub NG","NG=F",  "Petrochemical feedstock"),
    ),
    fred_series=(
        # NAPM was discontinued; ISM Manufacturing is no longer redistributed on FRED.
        # MANEMP (Manufacturing employees) and IPMAN (Industrial Production: Manufacturing)
        # are the closest free proxies. INDPRO is a broader fallback.
        FredSeries("US Manufacturing IP",   "IPMAN",                ""),
        FredSeries("Consumer Sentiment",    "UMCSENT",              ""),
    ),
    trends_queries=(
        TrendsQuery("Eating out interest",    ("eating out",)),
        TrendsQuery("Restaurant inflation",   ("restaurant prices",)),
    ),
    static_caption="Resin prices (ICIS/Platts) are subscription-only — not included.",
)


# ---------------------------------------------------------------------------
# Kelvion — heat exchangers
# ---------------------------------------------------------------------------

KELVION = Holding(
    key="kelvion",
    name="Kelvion",
    description="Heat exchangers across industrial, refrigeration, and data-centre cooling.",
    thesis="AI-driven data-centre buildout lifting liquid-cooling and HVAC demand; hyperscaler capex tailwind.",
    risk="Capex cycle reversal; community opposition to DC siting; competing cooling tech.",
    comps=(
        Comp("Alfa Laval",       "ALFA.ST", is_primary=True),
        Comp("GEA Group",        "G1A.DE"),
        Comp("Vertiv",           "VRT"),
        Comp("Munters",          "MTRS.ST"),
        Comp("Modine",           "MOD"),
    ),
    sparklines=(
        Sparkline("Industrials",            "XLI", "Broad industrial demand"),
        Sparkline("Infrastructure",         "IGF", "Capex / infra cycle proxy"),
    ),
    extra_tickers=(
        Sparkline("Nvidia",      "NVDA",  "AI compute leader"),
        Sparkline("CoreWeave",   "CRWV",  "Neocloud — pure-play GPU compute"),
        Sparkline("Nebius",      "NBIS",  "Neocloud — European GPU compute"),
    ),
    trends_queries=(
        TrendsQuery("DC protest",      ("data center protest",)),
        TrendsQuery("DC moratorium",   ("data center moratorium",)),
        TrendsQuery("DC water use",    ("data center water use",)),
    ),
    static_blocks=(
        StaticBlock(
            title="Hyperscaler quarterly capex",
            yaml_file="hyperscaler_capex.yaml",
            chart_kind="grouped_bar",
            caption="GOOGL, MSFT, META, AMZN — total quarterly capex from 10-Q filings.",
        ),
        StaticBlock(
            title="Neocloud quarterly capex",
            yaml_file="neocloud_capex.yaml",
            chart_kind="grouped_bar",
            caption="CoreWeave & Nebius capex disclosures.",
        ),
        StaticBlock(
            title="NVDA Data Center segment revenue",
            yaml_file="nvda_dc_revenue.yaml",
            chart_kind="bar",
            caption="Quarterly DC segment revenue from NVDA earnings releases.",
        ),
        StaticBlock(
            title="Global DC supply additions",
            yaml_file="dc_supply_additions.yaml",
            chart_kind="bar",
            caption="DC Byte / Synergy equivalents are subscription-only — figures here are hand-entered from public summaries.",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Real Chemistry — healthcare marketing services
# ---------------------------------------------------------------------------

REAL_CHEMISTRY = Holding(
    key="real_chemistry",
    name="Real Chemistry",
    description="Healthcare marketing services, real-world data, and HCP engagement.",
    thesis="Pharma marketing-spend cycle; growing demand for GLP-1 and obesity launch support.",
    risk="Drug-approval slowdown; biotech funding winter; pharma cost cuts; IRA pricing pressure.",
    comps=(
        Comp("IQVIA",             "IQV",   is_primary=True),
        Comp("Definitive Health", "DH"),
        Comp("Doximity",          "DOCS"),
        Comp("Veeva",             "VEEV"),
        Comp("Publicis Groupe",   "PUB.PA"),
    ),
    # Sparklines (sector ETFs) — pharma ETF selected at runtime; placeholder here is overridden.
    sparklines=(
        Sparkline("Pharma ETF (auto)", "XLV", "Most-liquid of XLV / IHE / XPH selected at runtime"),
        Sparkline("Health Insurers",   "IHF", "US healthcare providers"),
    ),
    fred_series=(
        FredSeries("US 10Y Real Yield", "DFII10", "%"),
        FredSeries("US 30Y Treasury",   "DGS30",  "%"),
    ),
    commodities=(
        Sparkline("EUR/USD", "EURUSD=X", "FX exposure on Publicis comp"),
    ),
    extra_tickers=(
        Sparkline("Biotech (XBI)", "XBI", "Biotech sentiment / funding proxy"),
    ),
    trends_queries=(
        TrendsQuery("GLP-1 interest", ("GLP-1",)),
        TrendsQuery("Ozempic interest", ("Ozempic",)),
    ),
    static_blocks=(
        StaticBlock(
            title="FDA novel drug approvals (NMEs)",
            yaml_file="fda_nme_approvals.yaml",
            chart_kind="bar",
            caption="CDER annual novel approvals (FDA).",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

HOLDINGS: dict[str, Holding] = {h.name: h for h in (NOVOLEX, KELVION, REAL_CHEMISTRY)}
HOLDING_ORDER = ("Novolex", "Kelvion", "Real Chemistry")


def get_holding(name: str) -> Holding:
    return HOLDINGS[name]
