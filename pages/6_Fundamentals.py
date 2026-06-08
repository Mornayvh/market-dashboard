"""
Company Fundamentals — Secco Capital.
SEC EDGAR 10-K fundamentals (capex, buybacks, issuances, diluted shares) for
the configured mega-cap set. Reads from the local SQLite DB
(data/fundamentals.db); refreshes from EDGAR on button click or via cron
(src/fundamentals_process.refresh_all).

Data conventions (do not drift — see src/config.py FUNDAMENTALS_METRICS):
values in millions; aligned to each filer's OWN fiscal year + period end;
capex = cash-flow "purchases of property & equipment"; share counts are not
split-normalized across filers.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import fundamentals_process as fp
from src.config import FUNDAMENTALS_TICKERS as TICKERS, FUNDAMENTALS_METRICS as METRICS
from src.viz_helpers import COLORS

st.set_page_config(
    page_title="Fundamentals | Secco Capital",
    page_icon="◼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS — Secco house style
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');
    .stApp { background-color: #F8FAFC; color: #1E293B; }
    .block-container { padding-top: 2rem; padding-bottom: 1rem; max-width: 1500px; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    header[data-testid="stHeader"] { background: #F8FAFC; }

    .fd-header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.75rem 0 1.25rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 1.25rem;
    }
    .fd-title { font-family: 'DM Sans', sans-serif; font-size: 1.4rem; font-weight: 700; color: #1E293B; letter-spacing: -0.02em; }
    .fd-subtitle { font-family: 'DM Sans', sans-serif; font-size: 0.8rem; color: #64748B; margin-top: 2px; }
    .fd-timestamp { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #64748B; text-align: right; }

    .section-header {
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600;
        color: #64748B; text-transform: uppercase; letter-spacing: 0.12em;
        padding: 1.1rem 0 0.5rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 0.8rem;
    }

    .stButton > button {
        background: #FFFFFF; color: #1E293B; border: 1px solid #CBD5E1;
        font-family: 'DM Sans', sans-serif; font-size: 0.78rem; font-weight: 600;
        border-radius: 4px; padding: 0.4rem 1.2rem;
    }
    .stButton > button:hover { background: #F1F5F9; border-color: #4F7FD6; color: #1E293B; }
</style>
""", unsafe_allow_html=True)


def section_header(text):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Chart styling — house palette applied to Plotly
# ---------------------------------------------------------------------------
# Qualitative per-ticker palette anchored on the house colours.
TICKER_PALETTE = [COLORS["accent"], COLORS["green"], "#1E3A8A",
                  COLORS["red"], COLORS["neutral"], COLORS["text_secondary"]]


def ticker_colors(tickers):
    return {t: TICKER_PALETTE[i % len(TICKER_PALETTE)]
            for i, t in enumerate(sorted(tickers))}


def style_fig(fig, height, y_title=""):
    """Apply the house chart style (transparent bg, slate grid, mono ticks)."""
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=COLORS["text_primary"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    font=dict(size=11, color=COLORS["text_secondary"])),
        xaxis=dict(showgrid=False, tickformat="d", dtick=1,
                   tickfont=dict(size=10, color=COLORS["text_secondary"],
                                 family="JetBrains Mono, monospace")),
        yaxis=dict(showgrid=True, gridcolor=COLORS["border"], zeroline=False,
                   title=dict(text=y_title, font=dict(size=11, color=COLORS["text_secondary"])),
                   tickfont=dict(size=10, color=COLORS["text_secondary"],
                                 family="JetBrains Mono, monospace")),
    )
    return fig


# ---------------------------------------------------------------------------
# Data access — cached DB read; refresh clears just this cache so other
# pages' (YF/FRED) caches survive a fundamentals refresh.
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_fundamentals(tickers: tuple):
    return fp.load_frame(tickers=list(tickers) or None)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
last = fp.get_last_refresh()
if last and last.get("run_at"):
    ts_text = (f"Last refresh: {pd.Timestamp(last['run_at']).strftime('%d %b %Y  %H:%M')} UTC"
               f" · {last.get('status')} · {last.get('rows_written')} rows")
else:
    ts_text = "No data yet"

st.markdown(
    f"""<div class="fd-header">
        <div><div class="fd-title">◼ Company Fundamentals</div>
        <div class="fd-subtitle">Capex, buybacks, issuances &amp; diluted shares from SEC 10-K filings ·
        values in millions · aligned to each filer's fiscal year</div></div>
        <div class="fd-timestamp">{ts_text}</div>
    </div>""",
    unsafe_allow_html=True,
)
if st.button("← Home", key="fd_home"):
    st.switch_page("app.py")

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------
col_a, col_b, col_c = st.columns([2, 2, 1])
with col_a:
    sel_tickers = st.multiselect("Companies", options=TICKERS, default=TICKERS)
with col_b:
    metric_keys = list(METRICS.keys())
    sel_metric = st.selectbox(
        "Metric", options=metric_keys,
        format_func=lambda k: METRICS[k]["name"], index=0)
with col_c:
    st.write("")
    refresh = st.button("Refresh from SEC", type="primary",
                        use_container_width=True)

if refresh:
    with st.spinner("Pulling company facts from SEC EDGAR…"):
        try:
            result = fp.refresh_all(tickers=sel_tickers or TICKERS)
            load_fundamentals.clear()  # so the read below sees the new rows
            st.success(f"Refreshed — {result['total_rows']} rows written.")
            # surface any metric that returned nothing (likely a tag-mapping gap)
            gaps = []
            for tk, cov in result["per_ticker"].items():
                if isinstance(cov, dict):
                    for m, n in cov.items():
                        if n == 0:
                            gaps.append(f"{tk}/{METRICS.get(m, {}).get('name', m)}")
            if gaps:
                st.warning("No data found for: " + ", ".join(gaps) +
                           " — these filers likely use a different XBRL tag. "
                           "Add the correct tag to FUNDAMENTALS_METRICS in src/config.py.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Refresh failed: {exc}")

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
df = load_fundamentals(tuple(sorted(sel_tickers)))
if df.empty:
    st.info("No data yet — click **Refresh from SEC** to pull the first batch.")
    st.stop()

unit_label = "$M" if METRICS[sel_metric]["unit"] == "USD" else "shares (M)"
tk_colors = ticker_colors(df["ticker"].unique())

# ---------------------------------------------------------------------------
# Trend chart
# ---------------------------------------------------------------------------
section_header(f"{METRICS[sel_metric]['name']} — Trend ({unit_label})")
trend = df[df["metric"] == sel_metric].sort_values("fiscal_year")
if not trend.empty:
    fig = go.Figure()
    for tk in sorted(trend["ticker"].unique()):
        sub = trend[trend["ticker"] == tk]
        fig.add_trace(go.Scatter(
            x=sub["fiscal_year"], y=sub["value_scaled"], name=tk,
            mode="lines+markers",
            line=dict(color=tk_colors[tk], width=2),
            marker=dict(size=6),
        ))
    st.plotly_chart(style_fig(fig, 420, unit_label), use_container_width=True)

# ---------------------------------------------------------------------------
# Latest-year comparison + combined repurchases vs issuances
# ---------------------------------------------------------------------------
left, right = st.columns(2)

with left:
    section_header(f"Latest Year — {METRICS[sel_metric]['name']}")
    if not trend.empty:
        latest_year = int(trend["fiscal_year"].max())
        snap = (trend[trend["fiscal_year"] == latest_year]
                .sort_values("value_scaled", ascending=False))
        bar = go.Figure(go.Bar(
            x=snap["ticker"], y=snap["value_scaled"],
            marker_color=[tk_colors[t] for t in snap["ticker"]],
        ))
        bar = style_fig(bar, 340, unit_label)
        bar.update_xaxes(tickformat=None, dtick=None, type="category",
                         tickfont=dict(family="DM Sans, sans-serif", size=11))
        st.plotly_chart(bar, use_container_width=True)
        st.caption(f"Fiscal year {latest_year} (per each filer's own year-end)")

with right:
    section_header("Combined Buybacks vs Issuances (shares, M)")
    rep = fp.pivot_metric(df, "repurchase_shares")
    iss = fp.pivot_metric(df, "issuance_shares")
    if not rep.empty or not iss.empty:
        years = sorted(set(rep.index) | set(iss.index))
        rep_tot = rep.reindex(years).sum(axis=1) if not rep.empty else pd.Series(0, index=years)
        iss_tot = iss.reindex(years).sum(axis=1) if not iss.empty else pd.Series(0, index=years)
        comb = go.Figure()
        comb.add_trace(go.Scatter(x=years, y=rep_tot, name="Repurchases",
                                  mode="lines+markers",
                                  line=dict(color=COLORS["accent"], width=2)))
        comb.add_trace(go.Scatter(x=years, y=iss_tot, name="Issuances",
                                  mode="lines+markers",
                                  line=dict(color=COLORS["neutral"], width=2)))
        st.plotly_chart(style_fig(comb, 340, "shares (M)"), use_container_width=True)
        st.caption("Note: share counts are not split-normalized across filers; "
                   "totals can be dominated by the largest-share-count company.")

# ---------------------------------------------------------------------------
# Detail table with provenance
# ---------------------------------------------------------------------------
section_header("Detail (with source filing)")
show = df[df["metric"] == sel_metric][[
    "ticker", "fiscal_year", "value_scaled", "period_end",
    "xbrl_tag", "source_accn"]].sort_values(["ticker", "fiscal_year"])
show = show.rename(columns={"value_scaled": unit_label,
                            "period_end": "fiscal period end",
                            "source_accn": "SEC accession"})
st.dataframe(show, use_container_width=True, hide_index=True)
st.caption("Source: SEC EDGAR companyfacts (10-K / 10-K/A annual values). "
           "Values keyed to each filing's own fiscal year and period end.")
