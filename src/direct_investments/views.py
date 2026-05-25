"""
views.py — Section renderers for the Direct Investments page.
Each render_* function consumes the Holding config + live data and emits Streamlit markup.
"""

from __future__ import annotations

import html
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.viz_helpers import COLORS, make_sparkline
from src.direct_investments import data_loader, static_loader
from src.direct_investments.config import (
    Holding, Sparkline, FredSeries, TrendsQuery, StaticBlock,
    PHARMA_ETF_CANDIDATES,
)


# ---------------------------------------------------------------------------
# Section header (matches existing dashboard style)
# ---------------------------------------------------------------------------

def section_header(text: str):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def _empty_caption(msg: str = "Data unavailable"):
    st.caption(msg)


def _fmt_pct(val: Optional[float]) -> str:
    if val is None or pd.isna(val):
        return "—"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%"


def _fmt_market_cap(val: Optional[float]) -> str:
    if val is None or pd.isna(val) or val == 0:
        return "—"
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    return f"${val/1e6:.0f}M"


def _fmt_price(val: Optional[float]) -> str:
    if val is None or pd.isna(val):
        return "—"
    if val >= 1000:
        return f"{val:,.2f}"
    return f"{val:.2f}"


def _tooltip_wrap(text: str, tooltip: str) -> str:
    """Wrap text in a span with a hoverable tooltip; falls back to plain text if no tooltip."""
    if not tooltip:
        return text
    esc = html.escape(tooltip, quote=True)
    return f'<span class="has-tooltip" data-tooltip="{esc}" title="{esc}">{text}</span>'


# ---------------------------------------------------------------------------
# Header block
# ---------------------------------------------------------------------------

def render_holding_header(holding: Holding):
    st.markdown(
        f"""<div class="holding-header">
            <div class="holding-name">{holding.name}</div>
            <div class="holding-desc">{holding.description}</div>
            <div class="holding-callouts">
                <span class="callout-thesis"><span class="callout-label">Thesis</span>{holding.thesis}</span>
                <span class="callout-risk"><span class="callout-label">Risk</span>{holding.risk}</span>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Public comparables
# ---------------------------------------------------------------------------

def render_comps(holding: Holding):
    section_header("Public Comparables")

    quotes = []
    for c in holding.comps:
        q = data_loader.fetch_quote(c.ticker)
        q["display"] = c.name
        q["is_primary"] = c.is_primary
        quotes.append(q)

    rationale_by_ticker = {c.ticker: c.rationale for c in holding.comps}

    rows_html = ""
    for q in quotes:
        chip = ' <span class="primary-chip">PRIMARY</span>' if q["is_primary"] else ""
        base_name = q["display"]
        wrapped = _tooltip_wrap(base_name, rationale_by_ticker.get(q["ticker"], ""))
        if q["is_primary"]:
            name_html = f'<span class="comp-name-primary">{wrapped}</span>{chip}'
        else:
            name_html = wrapped
        cells = [
            f'<td>{name_html}<span class="stock-ticker">{q["ticker"]}</span></td>',
            f'<td>{_fmt_price(q["price"])}</td>',
        ]
        for key in ("chg_1d", "chg_1w", "chg_1m", "chg_ytd"):
            v = q[key]
            color = COLORS["green"] if (v is not None and v > 0) else COLORS["red"] if (v is not None and v < 0) else COLORS["text_secondary"]
            cells.append(f'<td style="color:{color}">{_fmt_pct(v)}</td>')
        cells.append(f'<td>{_fmt_market_cap(q["market_cap"])}</td>')
        rows_html += "<tr>" + "".join(cells) + "</tr>"

    st.markdown(
        f"""<table class="data-table">
            <thead><tr>
                <th>Company</th><th>Price</th><th>1D</th><th>1W</th><th>1M</th><th>YTD</th><th>Mkt Cap</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>""",
        unsafe_allow_html=True,
    )

    # Rebased chart
    tickers = [c.ticker for c in holding.comps]
    primary = next((c.ticker for c in holding.comps if c.is_primary), None)
    rebased = data_loader.rebased_history(tickers, period="1y")
    if rebased.empty:
        _empty_caption("Rebased chart unavailable — price data could not be loaded.")
        return

    fig = go.Figure()
    palette = ["#94A3B8", "#94A3B8", "#94A3B8", "#94A3B8", "#94A3B8"]
    for i, tk in enumerate(rebased.columns):
        is_primary = (tk == primary)
        comp_name = next((c.name for c in holding.comps if c.ticker == tk), tk)
        fig.add_trace(go.Scatter(
            x=rebased.index,
            y=rebased[tk],
            mode="lines",
            line=dict(
                color=COLORS["accent"] if is_primary else palette[i % len(palette)],
                width=2.2 if is_primary else 1.0,
            ),
            opacity=1.0 if is_primary else 0.55,
            name=f"{comp_name} ({tk})",
            hovertemplate="%{y:.1f}<extra>%{fullData.name}</extra>",
        ))
    fig.update_layout(
        height=280,
        margin=dict(l=10, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(color=COLORS["text_secondary"], size=10)),
        yaxis=dict(
            showgrid=True, gridcolor=COLORS["border"], zeroline=False,
            tickfont=dict(color=COLORS["text_secondary"], size=10),
            title=dict(text="Rebased to 100", font=dict(size=10, color=COLORS["text_secondary"])),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, font=dict(size=10)),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Sparkline grid (sector ETFs, commodities, extra YF tickers)
# ---------------------------------------------------------------------------

def render_sparkline_grid(title: str, sparklines: list[Sparkline], days: int = 252):
    if not sparklines:
        return
    section_header(title)
    cols = st.columns(len(sparklines))
    for col, sp in zip(cols, sparklines):
        with col:
            df = data_loader.fetch_history(sp.ticker, period="1y")
            name_html = _tooltip_wrap(sp.name, sp.caption)
            label = f'<div class="spark-label"><span class="spark-name">{name_html}</span><span class="spark-ticker">{sp.ticker}</span></div>'
            if df is None or df.empty:
                st.markdown(label, unsafe_allow_html=True)
                _empty_caption("Data unavailable")
                continue

            first = float(df["Close"].iloc[0])
            last = float(df["Close"].iloc[-1])
            ltm_pct = (last / first - 1) * 100 if first else None
            color = COLORS["green"] if ltm_pct is not None and ltm_pct >= 0 else COLORS["red"]
            metric_html = (
                f'<div class="spark-metric">'
                f'<span class="spark-price">{_fmt_price(last)}</span> '
                f'<span style="color:{color}">{_fmt_pct(ltm_pct)} LTM</span>'
                f'</div>'
            )
            st.markdown(label + metric_html, unsafe_allow_html=True)
            fig = make_sparkline(df, name=sp.name, days=days, height=80)
            st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# FRED indicators (macro / industry)
# ---------------------------------------------------------------------------

def render_fred_indicators(title: str, series_list: list[FredSeries]):
    if not series_list:
        return
    section_header(title)
    cols = st.columns(len(series_list))
    for col, s in zip(cols, series_list):
        with col:
            df = data_loader.fetch_fred(s.series_id)
            name_html = _tooltip_wrap(s.name, s.caption)
            label = f'<div class="spark-label"><span class="spark-name">{name_html}</span><span class="spark-ticker">FRED: {s.series_id}</span></div>'
            if df is None or df.empty:
                st.markdown(label, unsafe_allow_html=True)
                _empty_caption("Data unavailable — set FRED_API_KEY")
                continue
            df = df.tail(365)
            last = float(df["Close"].iloc[-1])
            first = float(df["Close"].iloc[0])
            chg = last - first
            chg_color = COLORS["green"] if (chg >= 0) ^ s.invert_color else COLORS["red"]
            unit = s.unit_suffix
            metric_html = (
                f'<div class="spark-metric">'
                f'<span class="spark-price">{last:.2f}{unit}</span> '
                f'<span style="color:{chg_color}">{"+" if chg>=0 else ""}{chg:.2f}{unit} LTM</span>'
                f'</div>'
            )
            st.markdown(label + metric_html, unsafe_allow_html=True)
            fig = make_sparkline(df, name=s.name, days=252, height=80, invert_color=s.invert_color)
            st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Google Trends sentiment
# ---------------------------------------------------------------------------

def render_trends(title: str, queries: list[TrendsQuery], note: str = ""):
    if not queries:
        return
    section_header(title)

    series_frames = []
    labels = []
    for q in queries:
        df = data_loader.fetch_trends(q.keywords, geo=q.geo, timeframe=q.timeframe)
        if df is None or df.empty:
            continue
        # Sum across multiple keywords in the same query (usually it's one)
        col = q.keywords[0]
        if col in df.columns:
            series_frames.append(df[col].rename(q.label))
            labels.append(q.label)

    # Chip strip with per-query tooltips — shown regardless of whether data loaded
    chips = ""
    for q in queries:
        chip_inner = _tooltip_wrap(q.label, q.caption)
        chips += f'<span class="tooltip-chip">{chip_inner}</span>'
    if chips:
        st.markdown(f'<div class="tooltip-chip-row">{chips}</div>', unsafe_allow_html=True)

    if not series_frames:
        st.caption("Trends data unavailable — pytrends rate-limited or not installed.")
        return

    combined = pd.concat(series_frames, axis=1).ffill()
    fig = go.Figure()
    palette = [COLORS["accent"], "#16A34A", "#DC2626", "#F59E0B"]
    for i, col in enumerate(combined.columns):
        fig.add_trace(go.Scatter(
            x=combined.index, y=combined[col],
            mode="lines", line=dict(color=palette[i % len(palette)], width=1.6),
            name=col, hovertemplate="%{y}<extra>%{fullData.name}</extra>",
        ))
    fig.update_layout(
        height=220, margin=dict(l=10, r=20, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(color=COLORS["text_secondary"], size=10)),
        yaxis=dict(
            showgrid=True, gridcolor=COLORS["border"],
            tickfont=dict(color=COLORS["text_secondary"], size=10),
            title=dict(text="Search interest", font=dict(size=10, color=COLORS["text_secondary"])),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, font=dict(size=10)),
    )
    st.plotly_chart(fig, use_container_width=True)
    if note:
        st.caption(note)


# ---------------------------------------------------------------------------
# Static-data blocks
# ---------------------------------------------------------------------------

def _render_static_meta(meta: dict):
    parts = []
    if meta.get("last_updated"):
        parts.append(f"Last updated: {meta['last_updated']}")
    if meta.get("unit"):
        parts.append(meta["unit"])
    if parts:
        st.caption(" · ".join(parts))


def render_static_block(block: StaticBlock):
    section_header(block.title)

    if block.chart_kind == "grouped_bar":
        df, meta = static_loader.load_quarterly_long(block.yaml_file)
        if df.empty:
            _empty_caption(f"Static file empty or missing: data/static/{block.yaml_file}")
            return
        unit = meta.get("unit") or ""
        fig = go.Figure()
        companies = df["company"].unique().tolist()
        palette = ["#2563EB", "#16A34A", "#F59E0B", "#DC2626", "#94A3B8", "#0EA5E9"]
        for i, comp in enumerate(companies):
            sub = df[df["company"] == comp]
            fig.add_trace(go.Bar(
                x=sub["period"], y=sub["value"], name=comp,
                marker_color=palette[i % len(palette)],
            ))
        fig.update_layout(
            height=320, margin=dict(l=10, r=20, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            barmode="group", bargap=0.2,
            xaxis=dict(tickfont=dict(color=COLORS["text_secondary"], size=10)),
            yaxis=dict(
                showgrid=True, gridcolor=COLORS["border"],
                tickfont=dict(color=COLORS["text_secondary"], size=10),
                title=dict(text=unit, font=dict(size=10, color=COLORS["text_secondary"])),
            ),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, font=dict(size=10)),
        )
        st.plotly_chart(fig, use_container_width=True)
        if block.caption:
            st.caption(block.caption)
        _render_static_meta(meta)

    elif block.chart_kind == "bar":
        # Single-series bar — accept both quarterly long (one company) and simple-series schemas
        df_q, meta_q = static_loader.load_quarterly_long(block.yaml_file)
        if not df_q.empty:
            df, meta = df_q, meta_q
            x_vals, y_vals = df["period"], df["value"]
        else:
            df_s, meta_s = static_loader.load_simple_series(block.yaml_file)
            if df_s.empty:
                _empty_caption(f"Static file empty or missing: data/static/{block.yaml_file}")
                return
            df, meta = df_s, meta_s
            x_vals, y_vals = df["period"], df["value"]
        fig = go.Figure(go.Bar(x=x_vals, y=y_vals, marker_color=COLORS["accent"]))
        fig.update_layout(
            height=280, margin=dict(l=10, r=20, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickfont=dict(color=COLORS["text_secondary"], size=10)),
            yaxis=dict(
                showgrid=True, gridcolor=COLORS["border"],
                tickfont=dict(color=COLORS["text_secondary"], size=10),
                title=dict(text=meta.get("unit", ""), font=dict(size=10, color=COLORS["text_secondary"])),
            ),
        )
        st.plotly_chart(fig, use_container_width=True)
        if block.caption:
            st.caption(block.caption)
        _render_static_meta(meta)


# ---------------------------------------------------------------------------
# Real Chemistry-specific: pick the most-liquid pharma ETF at runtime
# ---------------------------------------------------------------------------

def resolve_real_chemistry_sparklines(holding: Holding) -> list[Sparkline]:
    """Replace the placeholder pharma sparkline with the most-liquid ETF choice."""
    chosen, volumes = data_loader.pick_most_liquid(list(PHARMA_ETF_CANDIDATES))
    label_map = {"XLV": "Health Care (XLV)", "IHE": "US Pharma (IHE)", "XPH": "S&P Pharma (XPH)"}
    pharma_caption = "Picked at runtime by 30-day avg dollar volume across XLV / IHE / XPH"
    resolved = []
    for s in holding.sparklines:
        if s.name.startswith("Pharma ETF"):
            resolved.append(Sparkline(label_map.get(chosen, chosen), chosen, pharma_caption))
        else:
            resolved.append(s)
    return resolved
