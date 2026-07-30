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
    currency: str = ""               # ISO code override; "" = take Yahoo's reported currency
    country: str = ""                # HQ country override for the flag; "" = take Yahoo's


@dataclass(frozen=True)
class Sparkline:
    name: str
    ticker: str
    caption: str = ""                # one-line "why this ETF/commodity matters"
    website: str = ""                # corporate site when the name is an operating company
    holdings_ticker: str = ""        # fund/ETF to pull top-10 holdings from (for an index,
                                     # its tracking ETF; for an ETF, itself). "" = no holdings box.
    currency: str = ""               # ISO code override; "" = take Yahoo's reported currency


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
    smooth: bool = False            # spline-smooth the line (line charts only)


@dataclass(frozen=True)
class CapexChart:
    """Quarterly capex grouped-bar pulled live from SEC EDGAR, with optional static overlay
    for non-EDGAR series (e.g. foreign 20-F filers with no 10-Q)."""
    title: str
    members: tuple                  # tuple[Comp] — name + ticker, pulled live from EDGAR
    caption: str = ""
    static_yaml: str = ""           # optional YAML for series EDGAR can't provide
    static_series: tuple = ()       # tuple[(yaml_company_key, display_name)] to pull from static_yaml


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
    capex_charts: tuple = ()         # tuple[CapexChart] — live quarterly capex charts (EDGAR)
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
                  "Float-adjusted market-cap-weighted index of the S&P 500's consumer "
                  "discretionary constituents (restaurants, retail, leisure) — an index "
                  "level, not a price. Read it as the market's forward view of "
                  "eating-out and discretionary retail volume, Novolex's largest "
                  "end-market. Sustained weakness signals fewer takeaway occasions and "
                  "so fewer packaging units, which hits Novolex on volume before price.",
                  holdings_ticker="XLY"),
        Sparkline("Consumer Staples",       "^SP500-30",
                  "Float-adjusted market-cap-weighted S&P 500 staples index — packaged "
                  "food, beverage and household-products makers, i.e. Novolex's CPG "
                  "buyers. Staples volumes are defensive, so this line usually holds up "
                  "when discretionary falls; if it rolls over too, the weakness is "
                  "broad-based demand rather than trading-down, and Novolex loses the "
                  "staples volume that normally cushions a consumer downturn.",
                  holdings_ticker="XLP"),
    ),
    commodities=(
        Sparkline("Brent",        "BZ=F",
                  "Front-month ICE Brent crude futures, USD per barrel — the marginal "
                  "price of the light sweet crude barrel, set daily by exchange trading. "
                  "Crude sets the naphtha cost that feeds polyethylene and polypropylene, "
                  "so Brent is the upstream floor under Novolex's resin bill. A sustained "
                  "rise compresses gross margin until price rises are passed through, "
                  "which typically lags one to two quarters on contracted volume.",
                  currency="USD"),
        Sparkline("Henry Hub NG", "NG=F",
                  "Front-month NYMEX natural gas futures, USD per million BTU, priced at "
                  "the Henry Hub, Louisiana. US crackers run on gas-derived ethane rather "
                  "than naphtha, so this is the more direct US resin-cost driver of the "
                  "two. Cheap US gas is a structural cost advantage for domestic "
                  "converters; a spike erodes it and raises both resin and plant energy "
                  "cost at once, hitting Novolex's cost base from two directions.",
                  currency="USD"),
    ),
    extra_tickers=(
        Sparkline("McDonald's",                  "MCD",
                  "Share price of the largest global QSR operator, ~40,000 outlets. "
                  "Moves on same-store sales and traffic guidance, so it is a sentiment "
                  "read on restaurant footfall rather than a packaging price. Falling "
                  "traffic guidance across the QSR set is the earliest public signal that "
                  "Novolex's food-service volume is about to soften; the equity turns "
                  "roughly a quarter before converter order books do.",
                  website="https://www.mcdonalds.com/"),
        Sparkline("Restaurant Brands Intl",      "QSR",
                  "Share price of the Burger King / Tim Hortons / Popeyes / Firehouse "
                  "group — a franchised multi-brand QSR operator, so the equity tracks "
                  "system-wide sales and net restaurant growth. Unit growth matters more "
                  "than price here: each net new outlet is incremental recurring packaging "
                  "demand, so a stalling store-opening programme caps Novolex's volume "
                  "growth even if traffic per store holds.",
                  website="https://www.rbi.com/"),
        Sparkline("Yum Brands",                  "YUM",
                  "Share price of the KFC / Taco Bell / Pizza Hut group, weighted heavily "
                  "to international markets. Useful as the ex-US leg of the QSR read: "
                  "divergence between this and the US-centric names tells you whether a "
                  "demand shift is domestic or global, which matters because Novolex's "
                  "exposure is predominantly North American.",
                  website="https://www.yum.com/"),
        Sparkline("Domino's Pizza",              "DPZ",
                  "Share price of the master franchisor, ~21,000 stores with a near-total "
                  "delivery and carryout mix. Because almost every order leaves the store "
                  "in packaging, this is the closest listed proxy for takeaway packaging "
                  "units — and it is corrugated and fibre rather than plastic, so it also "
                  "reads on the substitution side of the thesis alongside the recyclable "
                  "paper PPI.",
                  website="https://www.dominos.com/"),
        Sparkline("Chipotle",                    "CMG",
                  "Share price of the largest US fast-casual operator. Fast-casual uses "
                  "markedly more packaging per order than traditional QSR — bowls, lids, "
                  "bags — so this line is the read on packaging intensity per transaction "
                  "rather than transaction count. Share gains by fast-casual raise "
                  "Novolex's units per restaurant visit even with flat overall footfall.",
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
                   caption="Federal Reserve index of real output at US manufacturing "
                           "plants, monthly, built from physical output and production-hour "
                           "data rather than revenue — so it is a volume measure, not a "
                           "price one. It tracks how much product Novolex's industrial and "
                           "CPG customers are actually making, and therefore how many "
                           "containers and films they need to pack it in."),
        FredSeries("Consumer Sentiment",  "UMCSENT", "",
                   caption="University of Michigan index from a monthly household survey "
                           "on personal finances and buying conditions — an attitude "
                           "measure, so it leads spending rather than recording it. It is "
                           "the earliest of the three demand series here: sentiment turns, "
                           "then eating-out frequency, then Novolex's food-service order "
                           "volume, typically over one to two quarters."),
        FredSeries("Restaurant Employment", "CES7072200001", "",
                   caption="BLS payroll count for food services and drinking places, "
                           "monthly, from the establishment survey. Operators hire against "
                           "expected covers, so headcount is a committed, cash-backed "
                           "signal of expected traffic — harder evidence than sentiment. "
                           "It is the best free proxy for the served-meal volume that "
                           "drives Novolex's food-service packaging units."),
    ),
    fred_inputs=(
        FredSeries("Plastic Resins (PPI)", "WPU066", "",
                   caption="BLS producer price index for plastic resins and materials — "
                           "prices received by US resin producers at the factory gate, "
                           "monthly, before freight and converter margin. This is the "
                           "single largest line in Novolex's cost of goods. It moves ahead "
                           "of the reported P&L because resin is bought on contract, so a "
                           "step up here flags margin compression one to two quarters out "
                           "unless pass-through clauses catch it; watch the gap between "
                           "this and Brent for margin capture by the crackers."),
        FredSeries("Recyclable Paper (PPI)", "WPU0912", "",
                   caption="BLS producer price index for recyclable paper — the wastepaper "
                           "and recovered-fibre feedstock behind moulded-fibre and "
                           "paper-based packaging, monthly. Read it against the resin PPI "
                           "rather than alone: the spread between the two is the economics "
                           "of the plastic-to-fibre substitution that regulation is "
                           "pushing Novolex towards. Fibre cheapening relative to resin "
                           "makes the switch margin-accretive; the reverse makes "
                           "compliance costly."),
    ),
    trends_queries=(
        TrendsQuery("Eating out interest",  ("eating out",),
                    caption="Google search volume for the term, normalised 0-100 against "
                            "its own 12-month peak — a relative index, not a count, so "
                            "levels are not comparable between terms. Reads on intent to "
                            "dine out ahead of the transaction, making it the earliest "
                            "demand signal on this page for Novolex's food-service volume."),
        TrendsQuery("Restaurant inflation", ("restaurant prices",),
                    caption="Search interest in menu pricing, normalised 0-100. Rising "
                            "interest indicates price sensitivity, which precedes "
                            "trading down or eating at home. Both reduce served meals and "
                            "so reduce food-service packaging units — this is a risk "
                            "signal where the others are demand signals."),
        TrendsQuery("Food delivery",        ("food delivery",),
                    caption="Search interest in delivery, normalised 0-100. The most "
                            "margin-relevant term here: delivery and takeaway consume far "
                            "more packaging per meal than dine-in, so a shift towards "
                            "off-premise raises Novolex's units per restaurant visit even "
                            "with flat total covers."),
        TrendsQuery("Drive thru",           ("drive thru",),
                    caption="Search interest in drive-thru, normalised 0-100. Narrower "
                            "than the delivery term and specific to QSR rather than "
                            "restaurants generally — useful for separating a QSR-specific "
                            "move from a broad dining one, since Novolex's exposure is "
                            "weighted to quick-service."),
        TrendsQuery("DoorDash",             ("DoorDash",),
                    caption="Brand-name search interest, normalised 0-100. A branded proxy "
                            "for aggregator-led delivery volume; brand terms are noisier "
                            "than generic ones because marketing campaigns move them, so "
                            "treat divergence from the generic delivery term as a "
                            "marketing artefact before reading it as demand.",
                    website="https://www.doordash.com/"),
        # Regulatory-risk terms. Single-use plastic restrictions are the principal
        # structural threat to Novolex's plastics book and the driver of the
        # fibre-substitution case, so public salience is worth tracking alongside
        # demand. Unverified: Google Trends is currently unavailable (see
        # data_loader.fetch_trends), so these have not been checked for volume and
        # may return a flat or empty series when the feed is restored.
        TrendsQuery("Plastic ban",          ("plastic ban",),
                    caption="Search interest in plastic bans, normalised 0-100. A "
                            "salience measure, not a legislative tracker — it registers "
                            "public attention, which typically precedes state and "
                            "municipal action. Sustained elevation is the leading "
                            "indicator for Novolex's largest structural risk: regulatory "
                            "displacement of its single-use plastics volume."),
        TrendsQuery("Single-use plastic",   ("single use plastic",),
                    caption="Search interest in single-use plastic, normalised 0-100. The "
                            "term regulation is actually written against, so it is the "
                            "closer match to legislative language than the generic ban "
                            "term. Read the two together: attention rising on both is a "
                            "stronger signal of impending restriction than either alone."),
        TrendsQuery("Plastic packaging ban", ("plastic packaging ban",),
                    caption="Search interest in packaging-specific bans, normalised "
                            "0-100. Narrowest and most directly relevant of the three "
                            "regulatory terms, since it targets packaging rather than "
                            "bags or straws. Likely to be low-volume and therefore noisy "
                            "— treat direction over quarters, not week-to-week moves."),
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
                  "Float-adjusted market-cap-weighted index of the S&P 500's industrial "
                  "constituents — an index level, so no fund fees or tracking error. This "
                  "is the general capital-goods cycle Kelvion sells into outside data "
                  "centres. It sets the baseline: if this is rising and the AI-specific "
                  "lines below are flat, demand is broad industrial replacement rather "
                  "than the DC thesis playing out.",
                  holdings_ticker="XLI"),
        Sparkline("PHLX Semiconductor",  "^SOX",
                  "Modified market-cap-weighted index of US-listed semiconductor "
                  "designers and equipment makers, in points. Chip equities lead the AI "
                  "capex cycle because orders are placed before racks are installed and "
                  "long before cooling is commissioned — so this line turns roughly two "
                  "to four quarters ahead of Kelvion's heat-exchanger order intake. Treat "
                  "it as the earliest signal on the board, and the noisiest.",
                  holdings_ticker="SOXX"),
        Sparkline("S&P 500 Utilities", "^SP500-55",
                  "Float-adjusted cap-weighted S&P 500 utilities index — the generators "
                  "and grid operators that must supply data-centre load. Relevant as a "
                  "constraint rather than a demand signal: DC projects stall on power "
                  "availability, not on cooling capacity. Utility strength signals "
                  "generation capex being funded, which is what unblocks the DC pipeline "
                  "that Kelvion's order book ultimately depends on.",
                  holdings_ticker="XLU"),
        Sparkline("Global Infrastructure", "IGF",
                  "iShares Global Infrastructure ETF — a fund price, so it carries fees "
                  "and tracking error; used because no clean global infra index trades on "
                  "Yahoo. Proxies the large-project capex cycle worldwide. Kelvion's "
                  "revenue is project-linked with long lead times, so this reads on the "
                  "multi-year pipeline and financing conditions for big builds rather "
                  "than near-term shipments.",
                  holdings_ticker="IGF"),
    ),
    extra_tickers=(
        Sparkline("Nvidia",    "NVDA",
                  "Share price of the dominant AI accelerator vendor. Moves on data-centre "
                  "revenue and guidance, which is the closest public proxy for how much "
                  "compute is actually being installed. Rack power density scales with GPU "
                  "shipments, and cooling requirement scales with power density — so this "
                  "is the front of the chain that ends in Kelvion's addressable heat load, "
                  "with several quarters of lag.",
                  website="https://www.nvidia.com/"),
        Sparkline("CoreWeave", "CRWV",
                  "Share price of a pure-play GPU cloud operator. Unlike the hyperscalers, "
                  "essentially all its capex is data-centre buildout, so the equity is an "
                  "undiluted read on new DC capacity being financed and commissioned. Its "
                  "cost of capital matters directly: these builds are debt-funded, so "
                  "share-price weakness tightens financing and defers the projects Kelvion "
                  "would equip.",
                  website="https://www.coreweave.com/"),
        Sparkline("Nebius",    "NBIS",
                  "Share price of a European GPU-cloud operator. Carried specifically for "
                  "the EMEA leg — Kelvion is European, and European DC buildout runs on "
                  "different power, permitting and regulatory constraints from the US. "
                  "Divergence between this and CoreWeave tells you whether a slowdown is "
                  "global or confined to Kelvion's home region.",
                  website="https://www.nebius.com/"),
        Sparkline("Cerebras",  "CBRS",
                  "Share price of a wafer-scale AI chip designer, listed 14 May 2026 — so "
                  "the series is short and has no meaningful long-run history yet. Read "
                  "alongside Nvidia as a check on whether AI compute demand is broadening "
                  "beyond one vendor. Architecture matters here: wafer-scale parts have "
                  "different power and cooling profiles, which shifts the mix of heat "
                  "exchanger Kelvion would supply.",
                  website="https://www.cerebras.ai/"),
        # No data-centre index trades a usable series on Yahoo (the Dow Jones US
        # sub-indices return a single stale point), so this data-centre REIT fund
        # is the closest pure data-centre read available.
        Sparkline("Data Center REITs", "DTCR",
                  "Global X Data Center & Digital Infrastructure ETF — a fund price "
                  "tracking listed DC landlords and digital-infrastructure owners, so it "
                  "carries fees and tracking error. Used because no clean DC index trades "
                  "on Yahoo. Being REITs, it is rate-sensitive as well as demand-"
                  "sensitive: a fall may signal higher discount rates rather than weaker "
                  "DC demand, so check it against the GPU-cloud names before concluding "
                  "the buildout is slowing."),
    ),
    supplier_tickers=(
        Sparkline("Vistra",        "VST",
                  "Share price of an independent power producer and a major counterparty "
                  "on data-centre power purchase agreements. Read it as contracted power "
                  "supply being secured: PPAs are signed early in a DC project, so "
                  "strength here indicates projects clearing their binding power "
                  "constraint — the step that precedes the cooling specification Kelvion "
                  "bids into.",
                  website="https://www.vistracorp.com/"),
        Sparkline("Constellation", "CEG",
                  "Share price of a nuclear-heavy US utility, the archetype for firm "
                  "24/7 carbon-free DC supply. Nuclear-backed PPAs signal the highest-"
                  "conviction, longest-dated DC commitments, since they are contracted "
                  "over decades. That duration is what supports Kelvion's multi-year "
                  "order pipeline rather than a single build cycle.",
                  website="https://www.constellationenergy.com/"),
        Sparkline("Talen Energy",  "TLN",
                  "Share price of a nuclear and coal generator supplying dedicated DC "
                  "load. A second read on the same firm-power mechanism as Constellation; "
                  "carried so the signal does not rest on one counterparty. Divergence "
                  "between the two is usually company-specific rather than a change in "
                  "the DC power thesis.",
                  website="https://www.talenenergy.com/"),
        Sparkline("GE Vernova",    "GEV",
                  "Share price of a gas-turbine and grid-equipment maker. The closest "
                  "structural analogue to Kelvion on this board: long-cycle capital "
                  "equipment sold into the same DC buildout, with comparable lead times "
                  "and backlog dynamics. Its order intake and pricing power are the best "
                  "listed read on what Kelvion should be able to achieve on its own "
                  "backlog and margin.",
                  website="https://www.gevernova.com/"),
    ),
    fred_series=(
        FredSeries("Real GDP", "GDPC1", "",
                   caption="US real gross domestic product from the BEA, quarterly, in "
                           "chained dollars — inflation stripped out, so moves are real "
                           "volume. The broadest and slowest signal here: it confirms the "
                           "demand backdrop after the fact rather than leading it. Use it "
                           "as context for the two monthly series below, not as a trigger."),
        FredSeries("Industrial Production", "INDPRO", "",
                   caption="Federal Reserve index of real output across US manufacturing, "
                           "mining and utilities, monthly. More useful than GDP for "
                           "Kelvion because heat exchangers are sold into physical "
                           "process industries, and this measures physical output "
                           "directly. It also arrives monthly rather than quarterly, so "
                           "it turns well before GDP confirms."),
        FredSeries("Capacity Utilization", "TCU", "%",
                   caption="Output as a percentage of sustainable capacity, monthly from "
                           "the Federal Reserve. The most decision-relevant of the three: "
                           "plants running near capacity must add lines to grow, and new "
                           "lines need new heat exchangers. High and rising utilisation "
                           "is what converts industrial demand into Kelvion capex orders; "
                           "a fall means customers can absorb demand without buying kit."),
    ),
    trends_queries=(
        TrendsQuery("DC protest",    ("data center protest",),
                    caption="Google search volume for the term, normalised 0-100 against "
                            "its own 12-month peak — a relative index, not a count, so "
                            "levels are not comparable between terms. Local opposition is "
                            "the main non-technical reason DC projects slip, and a delayed "
                            "project defers Kelvion's order rather than cancelling it."),
        TrendsQuery("DC moratorium", ("data center moratorium",),
                    caption="Search interest in DC moratoria, normalised 0-100. Harder "
                            "than the protest term: a moratorium is formal municipal "
                            "action, so this registers opposition that has already "
                            "converted into policy. Sustained elevation points to sites "
                            "being blocked outright, which removes addressable demand "
                            "rather than delaying it."),
        TrendsQuery("DC water use",  ("data center water use",),
                    caption="Search interest in DC water consumption, normalised 0-100. "
                            "The one term here that can help rather than hurt: pressure on "
                            "water use pushes operators from evaporative cooling towards "
                            "closed-loop and dry systems, which is the heat-exchanger-"
                            "intensive specification Kelvion sells into. Read it as mix "
                            "shift, not demand loss."),
    ),
    capex_charts=(
        CapexChart(
            title="Hyperscaler quarterly capex",
            caption="Total-company capital expenditure by calendar quarter, derived live from 10-Q/10-K cash-flow filings via SEC EDGAR (YTD differenced; Microsoft's fiscal quarters fall into calendar quarters by period-end). Not split data-centre vs other.",
            members=(
                Comp("Alphabet",  "GOOGL"),
                Comp("Microsoft", "MSFT"),
                Comp("Meta",      "META"),
                Comp("Amazon",    "AMZN"),
            ),
        ),
        CapexChart(
            title="Neocloud quarterly capex",
            caption="CoreWeave capex by calendar quarter, live from 10-Q filings via SEC EDGAR. Nebius (Dutch 20-F filer — no quarterly US-GAAP filings) is hand-entered.",
            members=(Comp("CoreWeave", "CRWV"),),
            static_yaml="neocloud_capex.yaml",
            static_series=(("NBIS", "Nebius"),),
        ),
    ),
    static_blocks=(
        StaticBlock(
            title="NVDA Data Center segment revenue",
            yaml_file="nvda_dc_revenue.yaml",
            chart_kind="bar",
            caption="Quarterly DC segment revenue from NVDA earnings releases. (Segment-level data isn't exposed by SEC's XBRL API — it lives in dimensional tags — so this stays hand-entered.)",
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
                  "iShares U.S. Pharmaceuticals ETF — a fund price tracking large-cap US "
                  "pharma, so it carries fees and tracking error; used because no clean "
                  "pharma index trades on Yahoo. These are Real Chemistry's paying "
                  "clients. Read it for marketing-budget capacity: pharma commercial "
                  "spend is funded from product revenue, so this is the demand pool the "
                  "agency bills against, and it moves with patent cycles more than with "
                  "the broader market.",
                  holdings_ticker="IHE"),
        Sparkline("Health Insurers", "IHF",
                  "iShares U.S. Healthcare Providers ETF — payors and provider groups, "
                  "a fund price rather than an index. Relevant as the counterweight to "
                  "pharma: payor pressure on drug pricing compresses the margins that "
                  "fund promotional budgets. Payor strength alongside pharma weakness is "
                  "the configuration that squeezes agency spend hardest, so read the two "
                  "lines against each other rather than separately.",
                  holdings_ticker="IHF"),
        Sparkline("Biotech",         "XBI",
                  "SPDR S&P Biotech ETF — equal-weighted rather than cap-weighted, so it "
                  "reflects small and mid-cap biotech rather than being dominated by a "
                  "few large names. That makes it the cleanest read on early-stage "
                  "funding conditions. Emerging biotechs are the new-logo pipeline for "
                  "agency work: they commission launch campaigns only when financing is "
                  "open, so this is the most rate-sensitive and most forward-looking of "
                  "the three lines.",
                  holdings_ticker="XBI"),
    ),
    trends_queries=(
        TrendsQuery("GLP-1 interest",   ("GLP-1",),
                    caption="Search volume for the drug class, normalised 0-100 against "
                            "its own 12-month peak — a relative index, not a count. Proxies "
                            "consumer attention to the highest-spend therapeutic category "
                            "in the market. Launch and DTC campaign budgets follow public "
                            "attention, and those campaigns are the work Real Chemistry "
                            "bills for."),
        TrendsQuery("Ozempic interest", ("Ozempic",),
                    caption="Brand-level search interest, normalised 0-100. Narrower than "
                            "the class term and therefore a sharper read on a single "
                            "manufacturer's promotional push. Brand terms move on campaign "
                            "flighting, so a divergence from the class term usually "
                            "indicates marketing spend being switched on or off — which is "
                            "the agency revenue signal."),
    ),
    static_blocks=(
        StaticBlock(
            title="FDA novel drug approvals (NMEs)",
            yaml_file="fda_nme_approvals.yaml",
            chart_kind="line",
            caption="CDER annual novel approvals, 2000–2025 (FDA).",
            show_trend=True,
            smooth=True,
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
# SAP Fioneer — banking & insurance software (SAP–Dediq JV)
# NOTE: thesis/risk/description below are sector-accurate drafts — confirm against
# the actual holding's mandate and adjust the comp set as needed.
# ---------------------------------------------------------------------------

SAP_FIONEER = Holding(
    key="sap_fioneer",
    name="SAP Fioneer",
    description="Banking & insurance software platform (SAP–Dediq JV): core systems, cloud migration, embedded finance.",
    thesis="Financial institutions modernising core banking/insurance systems and moving to cloud; embedded-finance and regulation-driven IT demand.",
    risk="Long enterprise sales cycles; bank/insurer IT-budget sensitivity; competition from entrenched core-system vendors.",
    comps=(
        Comp("Temenos", "TEMN.SW", is_primary=True,
             rationale="Core banking software pure-play; closest public read on Fioneer's banking-platform market.",
             website="https://www.temenos.com/"),
        Comp("nCino", "NCNO",
             rationale="Cloud banking operating system; signal on banks' SaaS-platform adoption.",
             website="https://www.ncino.com/"),
        Comp("Q2 Holdings", "QTWO",
             rationale="Digital banking & lending platform; reads on mid-market bank software spend.",
             website="https://www.q2.com/"),
        Comp("Guidewire", "GWRE",
             rationale="Insurance core-systems leader; closest comp for Fioneer's insurance platform.",
             website="https://www.guidewire.com/"),
        Comp("FIS", "FIS",
             rationale="Large-scale banking & payments technology; broad financial-software demand baseline.",
             website="https://www.fisglobal.com/"),
        Comp("SAP", "SAP",
             rationale="Co-parent of the Fioneer JV; enterprise-software cycle and finance/ERP backdrop.",
             website="https://www.sap.com/"),
    ),
    sparklines=(
        Sparkline("S&P 500 Financials", "^SP500-40",
                  "Float-adjusted cap-weighted index of the S&P 500's financial "
                  "constituents — banks, insurers, capital markets — quoted in points, so "
                  "no fund fees or tracking error. This is Fioneer's entire customer base "
                  "in one line. Core-banking replacement is discretionary, multi-year and "
                  "board-approved, so it is funded out of customer profitability: sector "
                  "earnings weakness defers projects rather than cancelling them, which "
                  "shows up as a lengthening sales cycle before it shows up in revenue.",
                  holdings_ticker="XLF"),
        Sparkline("KBW Bank Index", "^BKX",
                  "Modified cap-weighted index of large US money-centre and regional "
                  "banks, in points. Narrower than the financials sector above and more "
                  "rate-sensitive, since bank earnings turn on net interest margin. Banks "
                  "are the core buyers of banking-platform software, so this is the "
                  "sharper read of the two — but note the exposure mismatch: Fioneer's "
                  "book is weighted to Europe, so treat this as a directional read on "
                  "bank IT budgets rather than a direct one.",
                  holdings_ticker="KBWB"),
        Sparkline("US Insurance (IAK)", "IAK",
                  "iShares U.S. Insurance ETF — a fund price covering property-casualty "
                  "and life insurers, with fees and tracking error. Insurance is the "
                  "second Fioneer platform and runs on a different cycle from banking: "
                  "insurer IT spend follows underwriting profitability and hard-market "
                  "pricing, not interest rates. Divergence from the bank index tells you "
                  "which of the two product lines is likely to carry the year.",
                  holdings_ticker="IAK"),
    ),
    trends_queries=(
        TrendsQuery("Core banking software", ("core banking software",),
                    caption="Search volume for the term, normalised 0-100 against its own "
                            "12-month peak — a relative index, not a count. The most "
                            "directly relevant term here: core-banking replacement is a "
                            "researched, committee-driven purchase, so search interest "
                            "reflects buyers early in an evaluation cycle that runs 12-24 "
                            "months before contract."),
        TrendsQuery("Digital banking", ("digital banking",),
                    caption="Search interest in digital banking, normalised 0-100. Much "
                            "broader than the core-banking term and includes consumer "
                            "searches for their own bank apps, so it is the noisiest line "
                            "here. Use it as background on digitisation salience rather "
                            "than as a procurement signal."),
        TrendsQuery("Insurtech", ("insurtech",),
                    caption="Search interest in insurtech, normalised 0-100, covering the "
                            "insurance-platform half of the business. Insurance IT "
                            "modernisation runs on a separate cycle from banking, so this "
                            "line is the check on whether the two product lines face the "
                            "same demand conditions or diverging ones."),
    ),
    website="https://www.sapfioneer.com/",
)


# ---------------------------------------------------------------------------
# Asia Restaurants — Asian QSR / casual-dining operator
# NOTE: the actual holding wasn't specified; this is modelled as an Asian
# restaurant operator with regional public comps. Confirm the company identity,
# thesis/risk, and comp set, and I'll refine.
# ---------------------------------------------------------------------------

ASIA_RESTAURANTS = Holding(
    key="asia_restaurants",
    name="Asia Restaurants",
    description="Southeast Asian quick-service & casual-dining operator across Thailand, Malaysia, Singapore, and Indonesia.",
    thesis="SE Asian dining-out growth: rising middle class, urbanisation, tourism recovery, and multi-brand QSR/casual expansion across ASEAN.",
    risk="Per-country FX and consumer cycles; tourism dependence; food & labour cost inflation; fragmented multi-market execution.",
    comps=(
        Comp("Minor International", "MINT.BK", is_primary=True,
             rationale="Thai multi-brand operator (The Pizza Company, Burger King TH, Swensen's, Sizzler); largest SE-Asia restaurant platform.",
             website="https://www.minor.com/"),
        Comp("MK Restaurant Group", "M.BK",
             rationale="Thai suki & Japanese-dining chain; mainland-Thailand dining-traffic read.",
             website="https://www.mkrestaurant.com/"),
        Comp("Berjaya Food", "5196.KL",
             rationale="Malaysian operator (Starbucks Malaysia, Kenny Rogers Roasters); Malaysia consumer read.",
             website="https://www.berjayafood.com/"),
        Comp("Jumbo Group", "42R.SI",
             rationale="Singapore seafood-restaurant group; tourism & dining-out proxy.",
             website="https://www.jumbogroup.sg/"),
        Comp("Kimly", "1D0.SI",
             rationale="Singapore coffee-shop & food-court operator; mass-market SE-Asia dining.",
             website="https://www.kimly.com.sg/"),
        Comp("Fast Food Indonesia", "FAST.JK",
             rationale="KFC Indonesia operator; Indonesian QSR demand and consumer recovery."),
    ),
    sparklines=(
        Sparkline("ASEAN equities (ASEA)", "ASEA",
                  "Global X FTSE Southeast Asia ETF — a fund price tracking a "
                  "cap-weighted basket of large ASEAN listings, so it carries tracking "
                  "error and fund fees unlike a raw index. Used because no SE-Asia "
                  "restaurant index trades on Yahoo. Read it as the regional risk "
                  "appetite and consumption backdrop: it sets the discount rate and exit "
                  "multiple environment for a private ASEAN dining asset more than it "
                  "predicts covers served.",
                  holdings_ticker="ASEA"),
        Sparkline("Straits Times (SG)", "^STI",
                  "Cap-weighted index of the largest Singapore Exchange listings, quoted "
                  "in index points. Singapore is the region's highest-spend dining market "
                  "and its most tourism-levered, so this is the read on premium covers "
                  "and inbound visitor spend. It matters for mix rather than volume: "
                  "Singapore weakness hits average ticket and margin harder than it hits "
                  "transaction count."),
        Sparkline("SET (Thailand)", "^SET.BK",
                  "Cap-weighted index of common shares listed on the Stock Exchange of "
                  "Thailand, in points. Thailand is the largest single market in the comp "
                  "set and the most tourism-sensitive of the three, so this line is the "
                  "cleanest read on whether a demand move is inbound-visitor driven or "
                  "domestic. Tourism-led softness tends to be sharper but shorter than "
                  "domestic consumer weakness."),
        Sparkline("Jakarta Composite (ID)", "^JKSE",
                  "Cap-weighted index of all shares listed on the Indonesia Stock "
                  "Exchange, in points. Indonesia is the largest population and the "
                  "structural growth leg of the thesis, so this is the long-duration "
                  "signal rather than the cyclical one. Read it for whether the "
                  "middle-class formation underpinning unit-expansion plans is still "
                  "being funded — it drives the store-opening runway, not this quarter's "
                  "covers."),
    ),
    website="",
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

HOLDINGS: dict[str, Holding] = {
    h.name: h for h in (NOVOLEX, KELVION, REAL_CHEMISTRY, SAP_FIONEER, ASIA_RESTAURANTS)
}
HOLDING_ORDER = ("Novolex", "Kelvion", "Real Chemistry", "SAP Fioneer", "Asia Restaurants")


def get_holding(name: str) -> Holding:
    return HOLDINGS[name]
