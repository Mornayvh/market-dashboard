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
    rationale: str = ""              # one-line "why we watch this comp"


@dataclass(frozen=True)
class Sparkline:
    name: str
    ticker: str
    caption: str = ""                # one-line "why this ETF/commodity matters"


@dataclass(frozen=True)
class FredSeries:
    name: str
    series_id: str
    unit_suffix: str = ""          # "%", "bps", etc.
    invert_color: bool = False     # True when "up = bad"
    caption: str = ""              # one-line "why this indicator matters"


@dataclass(frozen=True)
class TrendsQuery:
    label: str
    keywords: tuple                  # passed to pytrends as keyword list
    geo: str = "US"
    timeframe: str = "today 12-m"
    caption: str = ""                # one-line "why this search trend matters"


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
        Comp("Amcor",             "AMCR",      is_primary=True,
             rationale="Global packaging leader; closest read on Novolex's flexible + rigid product mix."),
        Comp("Sealed Air",        "SEE",
             rationale="Protective & food-packaging pure-play; same resin and freight cost exposure as Novolex."),
        Comp("Huhtamaki",         "HUH1V.HE",
             rationale="European food-service & retail packaging; signal on EMEA demand and pricing power."),
        Comp("Graphic Packaging", "GPK",
             rationale="Paperboard / folding cartons; cross-check on fibre-vs-plastics substitution dynamic."),
        Comp("Sonoco",            "SON",
             rationale="Diversified industrial packaging; reads on broader CPG buyer capex appetite."),
    ),
    sparklines=(
        Sparkline("Consumer Discretionary", "XLY",
                  "Restaurant traffic and dining demand — Novolex's largest end-market."),
        Sparkline("Consumer Staples",       "XLP",
                  "CPG buyers (food, household products) that drive Novolex packaging volumes."),
    ),
    commodities=(
        Sparkline("Brent",        "BZ=F",
                  "Crude benchmark; sets the cost floor for resin and polymer feedstocks."),
        Sparkline("WTI",          "CL=F",
                  "US crude; closer proxy for Novolex's domestic feedstock costs."),
        Sparkline("Henry Hub NG", "NG=F",
                  "Natural gas; key petrochemical input and a major US-specific cost variable."),
    ),
    fred_series=(
        # NAPM was discontinued; ISM Manufacturing is no longer redistributed on FRED.
        # MANEMP (Manufacturing employees) and IPMAN (Industrial Production: Manufacturing)
        # are the closest free proxies. INDPRO is a broader fallback.
        FredSeries("US Manufacturing IP", "IPMAN",   "",
                   caption="Industrial production for manufacturing — demand-side gauge for industrial-packaging customers."),
        FredSeries("Consumer Sentiment",  "UMCSENT", "",
                   caption="University of Michigan sentiment — leading indicator for eating-out and CPG spending."),
    ),
    trends_queries=(
        TrendsQuery("Eating out interest",  ("eating out",),
                    caption="Search interest as a proxy for restaurant demand; correlates with food-service packaging volume."),
        TrendsQuery("Restaurant inflation", ("restaurant prices",),
                    caption="Consumer awareness of menu prices; rising trend may signal restaurant-traffic risk."),
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
        Comp("Alfa Laval", "ALFA.ST", is_primary=True,
             rationale="Closest global heat-exchanger pure-play; primary read on Kelvion's core market."),
        Comp("GEA Group",  "G1A.DE",
             rationale="Direct industrial-cooling competitor; tracks the same European industrial cycle."),
        Comp("Vertiv",     "VRT",
             rationale="DC infrastructure leader; cleanest signal on data-centre capex flowing into cooling."),
        Comp("Munters",    "MTRS.ST",
             rationale="Climate solutions & DC air handling; complementary read on DC cooling demand."),
        Comp("Modine",     "MOD",
             rationale="Thermal management spanning HVAC and DC; reads on US liquid-cooling adoption."),
    ),
    sparklines=(
        Sparkline("Industrials",    "XLI",
                  "Broad industrial demand baseline that drives heat-exchanger order intake."),
        Sparkline("Infrastructure", "IGF",
                  "Global infra capex cycle proxy for large project pipeline."),
    ),
    extra_tickers=(
        Sparkline("Nvidia",    "NVDA",
                  "AI compute leader; DC buildout demand starts with GPU shipments."),
        Sparkline("CoreWeave", "CRWV",
                  "Pure-play GPU-cloud capex flowing directly into DC cooling demand."),
        Sparkline("Nebius",    "NBIS",
                  "European GPU cloud; useful for EMEA DC-buildout signal."),
    ),
    trends_queries=(
        TrendsQuery("DC protest",    ("data center protest",),
                    caption="Local opposition signal — permitting and siting risk for new DCs."),
        TrendsQuery("DC moratorium", ("data center moratorium",),
                    caption="Municipal action against DCs; quantifies the regulatory/political headwind."),
        TrendsQuery("DC water use",  ("data center water use",),
                    caption="Public concern over DC cooling water use; can shift cooling-tech specification."),
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
        Comp("IQVIA",             "IQV",    is_primary=True,
             rationale="Largest healthcare services & real-world data peer; primary read on pharma marketing and analytics spend."),
        Comp("Definitive Health", "DH",
             rationale="Healthcare commercial intelligence; tracks pharma R&D and commercial budget cycles."),
        Comp("Doximity",          "DOCS",
             rationale="Physician-engagement platform; direct read on HCP-marketing demand."),
        Comp("Veeva",             "VEEV",
             rationale="Life-sciences SaaS leader; signal on pharma's digital-marketing infrastructure spend."),
        Comp("Publicis Groupe",   "PUB.PA",
             rationale="Owner of Publicis Health, the largest healthcare marketing agency; direct comp on agency spend."),
    ),
    # Sparklines (sector ETFs) — pharma ETF selected at runtime; placeholder here is overridden.
    sparklines=(
        Sparkline("Pharma ETF (auto)", "XLV",
                  "Pharma sector return is the demand baseline for marketing-services spend. Most-liquid of XLV / IHE / XPH picked at runtime."),
        Sparkline("Health Insurers",   "IHF",
                  "US healthcare providers & payors; reads on payor-side budget environment."),
    ),
    fred_series=(
        FredSeries("US 10Y Real Yield", "DFII10", "%",
                   caption="Cost-of-capital input for pharma R&D and biotech funding cycles."),
        FredSeries("US 30Y Treasury",   "DGS30",  "%",
                   caption="Long-duration discount rate for pharma valuations & deal activity."),
    ),
    commodities=(
        Sparkline("EUR/USD", "EURUSD=X",
                  "FX cross used to translate Publicis performance; also captures EMEA pharma demand exposure."),
    ),
    extra_tickers=(
        Sparkline("Biotech (XBI)", "XBI",
                  "Cleanest read on early-stage biotech funding; drives launch and marketing budgets."),
    ),
    trends_queries=(
        TrendsQuery("GLP-1 interest",   ("GLP-1",),
                    caption="Search demand for the obesity-drug class; proxy for branded pharma launch marketing."),
        TrendsQuery("Ozempic interest", ("Ozempic",),
                    caption="Specific GLP-1 launch demand; bellwether for high-spend campaigns Real Chemistry services."),
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
