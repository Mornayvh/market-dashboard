"""
Portfolio Dashboard — Secco Capital Investment Map
Password-protected view of current and pipeline investments.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from collections import Counter

st.set_page_config(
    page_title="Portfolio Dashboard | Secco Capital",
    page_icon="◼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

    .stApp { background-color: #F8FAFC; color: #1E293B; }
    .block-container { padding-top: 2rem; padding-bottom: 1rem; max-width: 1400px; }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    header[data-testid="stHeader"] { background: #F8FAFC; }

    .port-header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.75rem 0 1.25rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 1.5rem;
    }
    .port-title {
        font-family: 'DM Sans', sans-serif; font-size: 1.4rem;
        font-weight: 700; color: #1E293B; letter-spacing: -0.02em;
    }
    .port-subtitle {
        font-family: 'DM Sans', sans-serif; font-size: 0.8rem; color: #64748B; margin-top: 2px;
    }

    .section-header {
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600;
        color: #64748B; text-transform: uppercase; letter-spacing: 0.12em;
        padding: 0.6rem 0 0.4rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 0.6rem;
    }

    .stat-card {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px;
        padding: 1rem 1.2rem; box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        min-height: 110px;
    }
    .stat-label {
        font-family: 'DM Sans', sans-serif; font-size: 0.7rem; font-weight: 500;
        color: #64748B; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.3rem;
    }
    .stat-value {
        font-family: 'JetBrains Mono', monospace; font-size: 1.4rem;
        font-weight: 700; color: #1E293B; line-height: 1.2;
        white-space: nowrap;
    }
    .stat-sub {
        font-family: 'DM Sans', sans-serif; font-size: 0.72rem; color: #64748B; margin-top: 0.2rem;
    }

    .data-table {
        width: 100%; border-collapse: collapse;
        font-family: 'JetBrains Mono', monospace; font-size: 0.74rem;
    }
    .data-table th {
        font-family: 'DM Sans', sans-serif; font-size: 0.63rem; font-weight: 600;
        color: #64748B; text-transform: uppercase; letter-spacing: 0.08em;
        padding: 0.5rem 0.5rem; border-bottom: 1px solid #E2E8F0; text-align: left;
    }
    .data-table td {
        padding: 0.5rem 0.5rem; border-bottom: 1px solid #F1F5F9; color: #1E293B;
    }
    .data-table tr:hover { background: #F1F5F9; }

    .tag {
        display: inline-block; background: #F1F5F9; border: 1px solid #E2E8F0;
        border-radius: 4px; padding: 2px 8px; margin: 1px 2px;
        font-family: 'DM Sans', sans-serif; font-size: 0.68rem; color: #334155;
    }
    .tag-invested { background: #DCFCE7; border-color: #BBF7D0; color: #166534; }
    .tag-pipeline { background: #FEF3C7; border-color: #FDE68A; color: #92400E; }

    .bar-row {
        display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;
    }
    .bar-label {
        font-family: 'DM Sans', sans-serif; font-size: 0.75rem; color: #1E293B;
        width: 140px; text-align: right; flex-shrink: 0;
    }
    .bar-track {
        flex: 1; height: 22px; background: #F1F5F9; border-radius: 4px; overflow: hidden;
    }
    .bar-fill {
        height: 100%; border-radius: 4px; display: flex; align-items: center;
        padding-left: 8px;
    }
    .bar-count {
        font-family: 'JetBrains Mono', monospace; font-size: 0.68rem;
        color: #FFFFFF; font-weight: 600;
    }

    .stButton > button {
        background: #2563EB; color: #FFFFFF; border: none;
        font-family: 'DM Sans', sans-serif; font-size: 0.85rem; font-weight: 600;
        border-radius: 6px; padding: 0.5rem 2rem;
    }
    .stButton > button:hover { background: #1D4ED8; color: #FFFFFF; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Password gate
# ---------------------------------------------------------------------------

def check_password():
    correct_pw = None
    try:
        correct_pw = st.secrets.get("portfolio", {}).get("password")
    except Exception:
        pass
    if not correct_pw:
        import os
        correct_pw = os.environ.get("PORTFOLIO_PASSWORD", "secco2026")

    if "portfolio_authenticated" not in st.session_state:
        st.session_state.portfolio_authenticated = False

    if st.session_state.portfolio_authenticated:
        return True

    st.markdown("")
    st.markdown("")
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="port-title" style="text-align:center; margin-bottom:0.5rem;">Portfolio Dashboard</div>', unsafe_allow_html=True)
        st.markdown('<div class="port-subtitle" style="text-align:center; margin-bottom:1.5rem;">Enter password to continue</div>', unsafe_allow_html=True)
        pw = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Enter password")
        if st.button("Access Dashboard", use_container_width=True):
            if pw == correct_pw:
                st.session_state.portfolio_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
    return False


if not check_password():
    st.stop()

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def load_portfolio():
    # Try multiple paths to find the Excel file
    possible_paths = [
        Path(__file__).parent.parent / "data" / "Internal_Investments_Dashboard.xlsx",
        Path.cwd() / "data" / "Internal_Investments_Dashboard.xlsx",
        Path("/mount/src/market-dashboard/data/Internal_Investments_Dashboard.xlsx"),
    ]
    
    xlsx_path = None
    for p in possible_paths:
        if p.exists():
            xlsx_path = p
            break
    
    if xlsx_path is None:
        st.error(f"Excel file not found. Searched: {[str(p) for p in possible_paths]}")
        return pd.DataFrame()

    df = pd.read_excel(xlsx_path, sheet_name="Investments Map Data")
    df.columns = [c.strip() for c in df.columns]

    def merge_cols(row, prefix, count):
        vals = []
        for i in range(count):
            col = prefix if i == 0 else f"{prefix} {i}"
            v = row.get(col)
            if pd.notna(v) and str(v).strip():
                vals.append(str(v).strip())
        return vals

    records = []
    for _, row in df.iterrows():
        partner = row.get("Partner")
        if pd.isna(partner) or not str(partner).strip():
            continue
        records.append({
            "partner": str(partner).strip(),
            "geographies": merge_cols(row, "Geography", 3),
            "min_ticket": row.get("Min ($)"),
            "max_ticket": row.get("Max ($)"),
            "asset_classes": merge_cols(row, "Asset Class / Strategy", 3),
            "stages": merge_cols(row, "Stage of Investment", 2),
            "invested": str(row.get("Invested", "")).strip(),
            "sectors": merge_cols(row, "Sector", 4),
        })

    return pd.DataFrame(records)


portfolio = load_portfolio()
if portfolio.empty:
    st.warning("No portfolio data loaded. Check that the Excel file is in the data/ folder.")
    st.stop()
invested = portfolio[portfolio["invested"] == "Invested"]
pipeline = portfolio[portfolio["invested"] == "Not Invested"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def section_header(text):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)

def stat_card(label, value, sub=""):
    sub_html = f'<div class="stat-sub">{sub}</div>' if sub else ""
    st.markdown(f'<div class="stat-card"><div class="stat-label">{label}</div><div class="stat-value">{value}</div>{sub_html}</div>', unsafe_allow_html=True)

def count_items(df, col):
    c = Counter()
    for items in df[col]:
        for item in items:
            c[item] += 1
    return c

def render_bar_chart(counts, color="#2563EB"):
    if not counts:
        return
    max_val = max(counts.values())
    html = ""
    for label, count in counts.most_common():
        pct = (count / max_val) * 100
        html += f'<div class="bar-row"><div class="bar-label">{label}</div><div class="bar-track"><div class="bar-fill" style="width:{pct}%; background:{color};"><span class="bar-count">{count}</span></div></div></div>'
    st.markdown(html, unsafe_allow_html=True)

def fmt_ticket(val):
    if pd.isna(val) or val is None:
        return "\u2014"
    v = float(val)
    if v >= 1e9:
        return f"${v/1e9:.0f}B"
    if v >= 1e6:
        return f"${v/1e6:.0f}M"
    return f"${v:,.0f}"

# ---------------------------------------------------------------------------
# World map
# ---------------------------------------------------------------------------

# Map region names to approximate lat/lon for plotting
GEO_COORDS = {
    "North America": (40, -100),
    "Europe": (50, 10),
    "Asia-Pacific": (20, 120),
    "South-East Asia": (5, 105),
    "India": (22, 78),
    "United Kingdom": (54, -2),
    "Global": (20, 0),
    "Global with exclusions": (20, 0),
    "Africa": (-5, 25),
    "Latin America": (-15, -60),
    "Middle East": (28, 45),
    "Japan": (36, 138),
    "China": (35, 105),
}

def build_world_map(df):
    """Build a Plotly world map showing geographic exposures."""
    geo_counts = count_items(df, "geographies")

    lats, lons, texts, sizes = [], [], [], []
    for geo, count in geo_counts.items():
        coords = GEO_COORDS.get(geo)
        if coords:
            lats.append(coords[0])
            lons.append(coords[1])
            texts.append(f"{geo}: {count} partner{'s' if count > 1 else ''}")
            sizes.append(max(12, count * 8))

    fig = go.Figure()

    fig.add_trace(go.Scattergeo(
        lat=lats, lon=lons,
        text=texts, hoverinfo="text",
        marker=dict(
            size=sizes,
            color="#2563EB",
            opacity=0.7,
            line=dict(width=1, color="#1D4ED8"),
        ),
    ))

    fig.update_geos(
        showcoastlines=True, coastlinecolor="#CBD5E1",
        showland=True, landcolor="#F8FAFC",
        showocean=True, oceancolor="#EFF6FF",
        showcountries=True, countrycolor="#E2E8F0",
        showframe=False,
        projection_type="natural earth",
    )

    fig.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        geo=dict(bgcolor="rgba(0,0,0,0)"),
        showlegend=False,
    )
    return fig

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

# Header
st.markdown("""<div class="port-header"><div><div class="port-title">\u25FC Portfolio Dashboard</div><div class="port-subtitle">Investment Allocation & Strategy Map</div></div></div>""", unsafe_allow_html=True)

# ── Summary cards ──
section_header("Summary")
c1, c2, c3, c4 = st.columns(4)
with c1:
    stat_card("Total Partners", str(len(portfolio)), f"{len(invested)} invested · {len(pipeline)} pipeline")
with c2:
    geo_count = len(count_items(invested, "geographies"))
    stat_card("Geographies", str(geo_count), "Distinct regions covered")
with c3:
    ac_count = len(count_items(invested, "asset_classes"))
    stat_card("Asset Classes", str(ac_count), "Strategies deployed")
with c4:
    min_tickets = invested["min_ticket"].dropna()
    max_tickets = invested["max_ticket"].dropna()
    if not min_tickets.empty and not max_tickets.empty:
        stat_card("Ticket Range", f"{fmt_ticket(min_tickets.min())} \u2013 {fmt_ticket(max_tickets.max())}", "Across invested partners")
    else:
        stat_card("Ticket Range", "\u2014")

st.markdown("<br>", unsafe_allow_html=True)

# ── World map ──
section_header("Geographic Exposure")
fig_map = build_world_map(invested)
st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# ── Breakdowns: two columns ──
left, right = st.columns([1, 1], gap="large")

with left:
    section_header("Geography Allocation")
    geo_invested = count_items(invested, "geographies")
    render_bar_chart(geo_invested, color="#2563EB")

    st.markdown("<br>", unsafe_allow_html=True)

    section_header("Asset Class / Strategy")
    ac_invested = count_items(invested, "asset_classes")
    render_bar_chart(ac_invested, color="#7C3AED")

    st.markdown("<br>", unsafe_allow_html=True)

    section_header("Sector Exposure")
    sec_invested = count_items(invested, "sectors")
    render_bar_chart(sec_invested, color="#0891B2")

with right:
    section_header("Investment Stage")
    stage_invested = count_items(invested, "stages")
    render_bar_chart(stage_invested, color="#059669")

    st.markdown("<br>", unsafe_allow_html=True)

    # Pipeline summary
    section_header("Pipeline")
    if not pipeline.empty:
        for _, row in pipeline.iterrows():
            geos = ", ".join(row["geographies"]) if row["geographies"] else "\u2014"
            acs = ", ".join(row["asset_classes"]) if row["asset_classes"] else "\u2014"
            stages = ", ".join(row["stages"]) if row["stages"] else "\u2014"
            sectors = ", ".join(row["sectors"]) if row["sectors"] else "\u2014"
            st.markdown(f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:0.7rem 1rem; margin-bottom:0.5rem; box-shadow:0 1px 2px rgba(0,0,0,0.04);"><div style="font-family:\'DM Sans\',sans-serif; font-size:0.82rem; font-weight:600; color:#1E293B;">{row["partner"]}</div><div style="font-family:\'DM Sans\',sans-serif; font-size:0.7rem; color:#64748B; margin-top:0.3rem;">{geos} · {acs} · {stages}</div><div style="font-family:\'DM Sans\',sans-serif; font-size:0.68rem; color:#94A3B8; margin-top:0.15rem;">{sectors} · {fmt_ticket(row["min_ticket"])} \u2013 {fmt_ticket(row["max_ticket"])}</div></div>', unsafe_allow_html=True)
    else:
        st.caption("No pipeline investments")

# ── Full data table ──
st.markdown("<br>", unsafe_allow_html=True)
section_header("All Investments")

rows_html = ""
for _, row in portfolio.iterrows():
    status_class = "tag-invested" if row["invested"] == "Invested" else "tag-pipeline"
    status_label = row["invested"]
    geos = ", ".join(row["geographies"]) if row["geographies"] else "\u2014"
    acs = ", ".join(row["asset_classes"]) if row["asset_classes"] else "\u2014"
    stages = ", ".join(row["stages"]) if row["stages"] else "\u2014"
    sectors = ", ".join(row["sectors"]) if row["sectors"] else "\u2014"
    ticket = f"{fmt_ticket(row['min_ticket'])} \u2013 {fmt_ticket(row['max_ticket'])}"

    rows_html += f"""<tr>
        <td style="font-family:'DM Sans',sans-serif; font-weight:500; font-size:0.76rem;">{row['partner']}</td>
        <td><span class="tag {status_class}">{status_label}</span></td>
        <td>{geos}</td>
        <td>{acs}</td>
        <td>{stages}</td>
        <td>{sectors}</td>
        <td style="text-align:right; white-space:nowrap;">{ticket}</td>
    </tr>"""

st.markdown(f"""<table class="data-table"><thead><tr><th>Partner</th><th>Status</th><th>Geography</th><th>Asset Class</th><th>Stage</th><th>Sector</th><th style="text-align:right;">Ticket Range</th></tr></thead><tbody>{rows_html}</tbody></table>""", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown('<div style="text-align:center; font-size:0.65rem; color:#94A3B8; font-family:\'DM Sans\',sans-serif;">Portfolio Dashboard · Secco Capital · Confidential · Not investment advice</div>', unsafe_allow_html=True)
