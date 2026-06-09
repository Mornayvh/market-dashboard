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
    website: str = ""                # corporate website (https://…)


@dataclass(frozen=True)
class Sparkline:
    name: str
    ticker: str
    caption: str = ""                # one-line "why this ETF/commodity matters"
    website: str = ""                # corporate site when the name is an operating company
    holdings_ticker: str = ""        # fund/ETF to pull top-10 holdings from (for an index,
                                     # its tracking ETF; for an ETF, itself). "" = no holdings box.


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
    website: str = ""                # corporate site when the label is a company brand


@dataclass(frozen=True)
class StaticBlock:
    """A static data section sourced from a hand-edited YAML."""
    title: str
    yaml_file: str
    chart_kind: str                 # "grouped_bar" | "line" | "bar"
    caption: str = ""
    show_trend: bool = False        # overlay a linear-fit trend line (bar charts only)


@dataclass(frozen=True)
class AdGroup:
    """A peer group whose annual advertising expense is pulled live from SEC EDGAR (USD)."""
    title: str
    members: tuple                  # tuple[Comp] — name + ticker
    caption: str = ""


@dataclass(frozen=True)
class Holding:
    key: str                         # url-safe slug
    name: str                        # display name
    description: str                 # one-liner
    thesis: str                      # what's working
    risk: str                        # what to watch
    comps: tuple                     # tuple[Comp]
    sparklines: tuple                # tuple[Sparkline] — sector ETFs / indices
    commodities: tuple = ()          # tuple[Sparkline]
    fred_series: tuple = ()          # tuple[FredSeries] — macro / demand indicators
    fred_inputs: tuple = ()          # tuple[FredSeries] — input-cost (PPI) series, rendered separately
    extra_tickers: tuple = ()        # tuple[Sparkline] for industry/sentiment YF series (XBI etc.)
    extra_tickers_title: str = "Industry & Sentiment"
    macro_title: str = "Macro"       # heading for the consolidated commodities + macro-FRED section
    supplier_tickers: tuple = ()     # tuple[Sparkline] for supply-side names (DC power, etc.)
    trends_queries: tuple = ()       # tuple[TrendsQuery]
    static_blocks: tuple = ()        # tuple[StaticBlock]
    ad_groups: tuple = ()            # tuple[AdGroup] — live advertising-spend peer charts (EDGAR)
    static_caption: Optional[str] = None
    website: str = ""                # corporate site for the holding itself


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
             rationale="Global packaging leader; closest read on Novolex's flexible + rigid product mix.",
             website="https://www.amcor.com/"),
        Comp("Silgan Holdings",   "SLGN",
             rationale="Rigid & dispensing packaging; closest mix to Novolex's flexible+rigid slate and same resin/freight exposure. (Replaced Sealed Air after CD&R took it private in Apr 2026.)",
             website="https://www.silganholdings.com/"),
        Comp("Huhtamaki",         "HUH1V.HE",
             rationale="European food-service & retail packaging; signal on EMEA demand and pricing power.",
             website="https://www.huhtamaki.com/"),
        Comp("Graphic Packaging", "GPK",
             rationale="Paperboard / folding cartons; cross-check on fibre-vs-plastics substitution dynamic.",
             website="https://www.graphicpkg.com/"),
        Comp("Sonoco",            "SON",
             rationale="Diversified industrial packaging; reads on broader CPG buyer capex appetite.",
             website="https://www.sonoco.com/"),
    ),
    sparklines=(
        Sparkline("Consumer Discretionary", "^SP500-25",
                  "Restaurant traffic and dining demand — Novolex's largest end-market. S&P 500 Consumer Discretionary index (no ETF tracking error).",
                  holdings_ticker="XLY"),
        Sparkline("Consumer Staples",       "^SP500-30",
                  "CPG buyers (food, household products) that drive Novolex packaging volumes. S&P 500 Consumer Staples index.",
                  holdings_ticker="XLP"),
    ),
    commodities=(
        Sparkline("Brent",        "BZ=F",
                  "Crude benchmark; sets the cost floor for resin and polymer feedstocks."),
        Sparkline("Henry Hub NG", "NG=F",
                  "Natural gas; key petrochemical input and a major US-specific cost variable."),
    ),
    extra_tickers=(
        Sparkline("McDonald's",                  "MCD",
                  "Global QSR bellwether; broadest read on QSR traffic and packaging volume.",
                  website="https://www.mcdonalds.com/"),
        Sparkline("Restaurant Brands Intl",      "QSR",
                  "Burger King, Tim Hortons, Popeyes, Firehouse Subs — pure QSR play.",
                  website="https://www.rbi.com/"),
        Sparkline("Yum Brands",                  "YUM",
                  "KFC, Taco Bell, Pizza Hut — international QSR mix.",
                  website="https://www.yum.com/"),
        Sparkline("Chipotle",                    "CMG",
                  "Fast-casual leader; bowl/bag packaging signal.",
                  website="https://www.chipotle.com/"),
    ),
    # No clean QSR/restaurant index trades a usable series on Yahoo (Dow Jones US
    # Restaurants & Bars ^DJUSRU returns only a single stale point), so these
    # large-cap QSR names remain the read on quick-service restaurant volume.
    extra_tickers_title="QSR",
    macro_title="Supply Chain",
    fred_series=(
        # NAPM was discontinued; ISM Manufacturing is no longer redistributed on FRED.
        # MANEMP (Manufacturing employees) and IPMAN (Industrial Production: Manufacturing)
        # are the closest free proxies. INDPRO is a broader fallback.
        FredSeries("US Manufacturing IP", "IPMAN",   "",
                   caption="Industrial production for manufacturing — demand-side gauge for industrial-packaging customers."),
        FredSeries("Consumer Sentiment",  "UMCSENT", "",
                   caption="University of Michigan sentiment — leading indicator for eating-out and CPG spending."),
        FredSeries("Restaurant Employment", "CES7072200001", "",
                   caption="Food services & drinking places employment — leading demand indicator for QSR packaging volume."),
    ),
    fred_inputs=(
        FredSeries("Plastic Resins (PPI)", "WPU066", "",
                   caption="PPI for plastic resins and materials — virgin-resin headline input cost."),
        FredSeries("Recyclable Paper (PPI)", "WPU0912", "",
                   caption="PPI for recyclable paper — fibre input cost; cross-check on paper-vs-plastic substitution."),
    ),
    trends_queries=(
        TrendsQuery("Eating out interest",  ("eating out",),
                    caption="Search interest as a proxy for restaurant demand; correlates with food-service packaging volume."),
        TrendsQuery("Restaurant inflation", ("restaurant prices",),
                    caption="Consumer awareness of menu prices; rising trend may signal restaurant-traffic risk."),
        TrendsQuery("Food delivery",        ("food delivery",),
                    caption="Off-premise demand proxy; drives single-use takeout packaging volume."),
        TrendsQuery("Drive thru",           ("drive thru",),
                    caption="Drive-thru search interest — narrow proxy for QSR-specific traffic vs broader restaurant demand."),
        TrendsQuery("DoorDash",             ("DoorDash",),
                    caption="Delivery-app brand sentiment; correlates with takeout-packaging consumption.",
                    website="https://www.doordash.com/"),
    ),
    static_caption="ICIS/Platts spot resin tickers remain subscription-only — FRED PPI series above are the free monthly proxy.",
    website="https://www.novolex.com/",
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
             rationale="Closest global heat-exchanger pure-play; primary read on Kelvion's core market.",
             website="https://www.alfalaval.com/"),
        Comp("GEA Group",  "G1A.DE",
             rationale="Direct industrial-cooling competitor; tracks the same European industrial cycle.",
             website="https://www.gea.com/"),
        Comp("Vertiv",     "VRT",
             rationale="DC infrastructure leader; cleanest signal on data-centre capex flowing into cooling.",
             website="https://www.vertiv.com/"),
        Comp("Munters",    "MTRS.ST",
             rationale="Climate solutions & DC air handling; complementary read on DC cooling demand.",
             website="https://www.munters.com/"),
        Comp("Modine",     "MOD",
             rationale="Thermal management spanning HVAC and DC; reads on US liquid-cooling adoption.",
             website="https://www.modine.com/"),
    ),
    sparklines=(
        Sparkline("S&P 500 Industrials", "^SP500-20",
                  "S&P 500 Industrials sector index — pure market signal, no ETF tracking error.",
                  holdings_ticker="XLI"),
        Sparkline("PHLX Semiconductor",  "^SOX",
                  "Established US chip-stocks index (Philadelphia Semiconductor); AI capex cycle driver for DC cooling demand.",
                  holdings_ticker="SOXX"),
        Sparkline("S&P 500 Utilities", "^SP500-55",
                  "Power-utility sector index — the generation/grid names that supply data-centre load; clean index, no ETF tracking error.",
                  holdings_ticker="XLU"),
        Sparkline("Global Infrastructure", "IGF",
                  "Global infra capex cycle proxy for large project pipeline. ETF — no clean Yahoo index alternative.",
                  holdings_ticker="IGF"),
    ),
    extra_tickers=(
        Sparkline("Nvidia",    "NVDA",
                  "AI compute leader; DC buildout demand starts with GPU shipments.",
                  website="https://www.nvidia.com/"),
        Sparkline("CoreWeave", "CRWV",
                  "Pure-play GPU-cloud capex flowing directly into DC cooling demand.",
                  website="https://www.coreweave.com/"),
        Sparkline("Nebius",    "NBIS",
                  "European GPU cloud; useful for EMEA DC-buildout signal.",
                  website="https://www.nebius.com/"),
        Sparkline("Cerebras",  "CBRS",
                  "Wafer-scale AI chip designer; IPO'd May 2026. Alternative AI-compute build read alongside Nvidia.",
                  website="https://www.cerebras.ai/"),
        # No data-centre index trades a usable series on Yahoo (the Dow Jones US
        # sub-indices return a single stale point), so this data-centre REIT fund
        # is the closest pure data-centre read available.
        Sparkline("Data Center REITs", "DTCR",
                  "Global X Data Center & Digital Infrastructure ETF — closest pure data-centre read; no clean Yahoo DC index exists."),
    ),
    supplier_tickers=(
        Sparkline("Vistra",        "VST",
                  "Independent power producer; major DC PPA counterparty (Microsoft, Amazon).",
                  website="https://www.vistracorp.com/"),
        Sparkline("Constellation", "CEG",
                  "Nuclear-heavy utility; Three Mile Island restart deal with Microsoft anchors DC supply.",
                  website="https://www.constellationenergy.com/"),
        Sparkline("Talen Energy",  "TLN",
                  "Nuclear/coal producer; Susquehanna PPA powering AWS's Cumulus DC complex.",
                  website="https://www.talenenergy.com/"),
        Sparkline("GE Vernova",    "GEV",
                  "Gas turbines & grid equipment; supplies the generation capacity behind new DC sites.",
                  website="https://www.gevernova.com/"),
    ),
    fred_series=(
        FredSeries("Real GDP", "GDPC1", "",
                   caption="Headline US real GDP — broad demand baseline. Quarterly series."),
        FredSeries("Industrial Production", "INDPRO", "",
                   caption="Monthly US industrial output — cleaner read on Kelvion's industrial-customer demand than GDP."),
        FredSeries("Capacity Utilization", "TCU", "%",
                   caption="How hard US plants are running — leading indicator of replacement / expansion capex for cooling kit."),
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
    website="https://www.kelvion.com/",
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
             rationale="Largest healthcare services & real-world data peer; primary read on pharma marketing and analytics spend.",
             website="https://www.iqvia.com/"),
        Comp("Definitive Health", "DH",
             rationale="Healthcare commercial intelligence; tracks pharma R&D and commercial budget cycles.",
             website="https://www.definitivehc.com/"),
        Comp("Doximity",          "DOCS",
             rationale="Physician-engagement platform; direct read on HCP-marketing demand.",
             website="https://www.doximity.com/"),
        Comp("Veeva",             "VEEV",
             rationale="Life-sciences SaaS leader; signal on pharma's digital-marketing infrastructure spend.",
             website="https://www.veeva.com/"),
        Comp("Publicis Groupe",   "PUB.PA",
             rationale="Owner of Publicis Health, the largest healthcare marketing agency; direct comp on agency spend.",
             website="https://www.publicisgroupe.com/"),
    ),
    sparklines=(
        # No usable Yahoo index exists for these pharma/biotech sub-sectors (the
        # Dow Jones US Pharmaceuticals / Biotechnology indices return only a single
        # stale point), so the sector ETFs are retained as the cleanest proxy.
        Sparkline("Pharmaceuticals", "IHE",
                  "iShares U.S. Pharmaceuticals ETF — pharma-specific demand baseline; no clean Yahoo pharma index exists.",
                  holdings_ticker="IHE"),
        Sparkline("Health Insurers", "IHF",
                  "US healthcare providers & payors ETF; reads on payor-side budget environment. No clean Yahoo sub-sector index.",
                  holdings_ticker="IHF"),
        Sparkline("Biotech",         "XBI",
                  "SPDR biotech ETF — cleanest read on early-stage biotech funding; no clean Yahoo biotech index exists.",
                  holdings_ticker="XBI"),
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
            chart_kind="line",
            caption="CDER annual novel approvals, 2000–2025 (FDA).",
            show_trend=True,
        ),
    ),
    ad_groups=(
        AdGroup(
            title="Large-cap pharma advertising spend",
            caption="Annual advertising expense (US-GAAP AdvertisingExpense) from 10-K filings via SEC EDGAR — actual paid advertising / DTC media spend, not broad SG&A. Foreign-listed peers (Novartis, AstraZeneca, GSK) file under IFRS and don't disclose advertising separately, so they're omitted.",
            members=(
                Comp("Pfizer",    "PFE"),
                Comp("Merck",     "MRK"),
                Comp("Eli Lilly", "LLY"),
            ),
        ),
        AdGroup(
            title="Specialty biotech advertising spend",
            caption="Annual advertising expense (US-GAAP AdvertisingExpense) from 10-K filings via SEC EDGAR. Peers that don't disclose advertising (Ionis) or aren't SEC filers (Galderma, Sobi, Otsuka) are omitted.",
            members=(
                Comp("Incyte",      "INCY"),
                Comp("Jazz Pharma", "JAZZ"),
            ),
        ),
    ),
    website="https://www.realchemistry.com/",
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

HOLDINGS: dict[str, Holding] = {h.name: h for h in (NOVOLEX, KELVION, REAL_CHEMISTRY)}
HOLDING_ORDER = ("Novolex", "Kelvion", "Real Chemistry")


def get_holding(name: str) -> Holding:
    return HOLDINGS[name]
