"""
views.py — Section renderers for the Direct Investments page.
Each render_* function consumes the Holding config + live data and emits Streamlit markup.
"""

from __future__ import annotations

import html
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.viz_helpers import COLORS, make_sparkline
from src.direct_investments import data_loader, static_loader
from src.direct_investments.config import (
    Holding, Sparkline, FredSeries, TrendsQuery, StaticBlock,
)

# Navy palette for column/bar charts — shades of navy blue with enough lightness
# spread between adjacent steps to stay legible in grouped bars. Dark → light.
NAVY_PALETTE = ["#0A2A4A", "#15528A", "#2E7BC4", "#5BA0DA", "#93C0EA", "#C7DEF4"]
NAVY_BAR = "#15528A"   # single-series bar fill


# ---------------------------------------------------------------------------
# Section header (matches existing dashboard style)
# ---------------------------------------------------------------------------

def section_header(text: str):
    if not text:   # allow sub-grids to render headerless under a shared section
        return
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


def _link_wrap(inner_html: str, url: str) -> str:
    """Wrap inner HTML in an anchor opening in a new tab; returns inner unchanged if no url."""
    if not url:
        return inner_html
    href = html.escape(url, quote=True)
    return f'<a href="{href}" target="_blank" rel="noopener noreferrer" class="comp-link">{inner_html}</a>'


# ---------------------------------------------------------------------------
# Header block
# ---------------------------------------------------------------------------

def render_holding_header(holding: Holding):
    name_html = _link_wrap(holding.name, getattr(holding, "website", ""))
    st.markdown(
        f"""<div class="holding-header">
            <div class="holding-name">{name_html}</div>
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
    website_by_ticker = {c.ticker: c.website for c in holding.comps}

    rows_html = ""
    for q in quotes:
        chip = ' <span class="primary-chip">PRIMARY</span>' if q["is_primary"] else ""
        base_name = q["display"]
        wrapped = _tooltip_wrap(base_name, rationale_by_ticker.get(q["ticker"], ""))
        website = website_by_ticker.get(q["ticker"], "")
        if website:
            href = html.escape(website, quote=True)
            wrapped = f'<a href="{href}" target="_blank" rel="noopener noreferrer" class="comp-link">{wrapped}</a>'
        if q["is_primary"]:
            name_html = f'<span class="comp-name-primary">{wrapped}</span>{chip}'
        else:
            name_html = wrapped
        cells = [
            f'<td>{name_html}<span class="stock-ticker">{q["ticker"]}</span></td>',
            f'<td>{_fmt_price(q["price"])}</td>',
        ]
        for key in ("chg_1d", "chg_1w", "chg_1m", "chg_ltm"):
            v = q[key]
            color = COLORS["green"] if (v is not None and v > 0) else COLORS["red"] if (v is not None and v < 0) else COLORS["text_secondary"]
            cells.append(f'<td style="color:{color}">{_fmt_pct(v)}</td>')
        cells.append(f'<td>{_fmt_market_cap(q["market_cap"])}</td>')
        rows_html += "<tr>" + "".join(cells) + "</tr>"

    st.markdown(
        f"""<table class="data-table">
            <thead><tr>
                <th>Company</th><th>Price</th><th>1D</th><th>1W</th><th>1M</th><th>LTM</th><th>Mkt Cap</th>
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
    # Distinct muted palette for non-primary lines; primary uses the accent blue.
    palette = ["#94A3B8", "#6366F1", "#F59E0B", "#14B8A6", "#EC4899"]
    palette_idx = 0
    for tk in rebased.columns:
        is_primary = (tk == primary)
        comp_name = next((c.name for c in holding.comps if c.ticker == tk), tk)
        if is_primary:
            color = COLORS["accent"]
        else:
            color = palette[palette_idx % len(palette)]
            palette_idx += 1
        fig.add_trace(go.Scatter(
            x=rebased.index,
            y=rebased[tk],
            mode="lines",
            line=dict(color=color, width=2.4 if is_primary else 1.4),
            opacity=1.0 if is_primary else 0.75,
            name=f"{comp_name} ({tk})",
            hovertemplate="%{y:.1f}<extra>%{fullData.name}</extra>",
        ))
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=20, t=20, b=90),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(color=COLORS["text_secondary"], size=10)),
        yaxis=dict(
            showgrid=True, gridcolor=COLORS["border"], zeroline=False,
            tickfont=dict(color=COLORS["text_secondary"], size=10),
            title=dict(text="Rebased to 100", font=dict(size=10, color=COLORS["text_secondary"])),
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top", y=-0.15,
            xanchor="center", x=0.5,
            font=dict(size=11, color=COLORS["text_primary"]),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Sparkline grid (sector ETFs, commodities, extra YF tickers)
# ---------------------------------------------------------------------------

def _render_holdings_popover(sp: Sparkline):
    """Click-to-open box with the benchmark's top-10 holdings + weights (via tracking ETF)."""
    ht = getattr(sp, "holdings_ticker", "")
    if not ht:
        return
    holdings = data_loader.fetch_top_holdings(ht)
    with st.popover("ⓘ Top 10 holdings", use_container_width=True):
        if not holdings:
            st.caption("Holdings data unavailable.")
            return
        if ht != sp.ticker:
            st.caption(
                f"Top 10 holdings of {ht} — the ETF that tracks {sp.name} ({sp.ticker}). "
                "Index constituents aren't published via the data feed, so the tracking "
                "ETF's holdings stand in; weights are the ETF's and may differ marginally."
            )
        else:
            st.caption(f"Top 10 holdings of {sp.name} ({sp.ticker}).")
        rows = ""
        for sym, name, w in holdings:
            disp = name if len(name) <= 34 else name[:33] + "…"
            rows += (
                f'<tr><td>{html.escape(disp)}</td>'
                f'<td>{html.escape(sym)}</td><td>{w:.2f}%</td></tr>'
            )
        st.markdown(
            '<table class="data-table"><thead><tr>'
            '<th>Company</th><th>Ticker</th><th>Weight</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>',
            unsafe_allow_html=True,
        )


def render_sparkline_grid(title: str, sparklines: list[Sparkline], days: int = 252):
    if not sparklines:
        return
    section_header(title)
    cols = st.columns(len(sparklines))
    for col, sp in zip(cols, sparklines):
        with col:
            df = data_loader.fetch_history(sp.ticker, period="1y")
            name_html = _tooltip_wrap(sp.name, sp.caption)
            name_html = _link_wrap(name_html, getattr(sp, "website", ""))
            label = f'<div class="spark-label"><span class="spark-name">{name_html}</span><span class="spark-ticker">{sp.ticker}</span></div>'
            if df is None or df.empty:
                st.markdown(label, unsafe_allow_html=True)
                _empty_caption("Data unavailable")
                _render_holdings_popover(sp)
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
            _render_holdings_popover(sp)


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

    # Leading (i) icon explaining how the chart works, then a chip per query.
    info_text = (
        "Google Trends search interest, normalised 0–100 (100 = the term's peak "
        "over the window), trailing 12 months, US. Each line tracks one search term. "
        "These chips are hover-labels, not buttons — hover one to see what it proxies. "
        "To hide or show a line, click its name in the legend below the chart."
    )
    info_esc = html.escape(info_text, quote=True)
    chips = (
        f'<span class="has-tooltip info-icon" data-tooltip="{info_esc}" title="{info_esc}">i</span>'
    )
    for q in queries:
        chip_inner = _tooltip_wrap(q.label, q.caption)
        chip_inner = _link_wrap(chip_inner, getattr(q, "website", ""))
        chips += f'<span class="tooltip-chip">{chip_inner}</span>'
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
        for i, comp in enumerate(companies):
            sub = df[df["company"] == comp]
            fig.add_trace(go.Bar(
                x=sub["period"], y=sub["value"], name=comp,
                marker_color=NAVY_PALETTE[i % len(NAVY_PALETTE)],
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
        fig = go.Figure(go.Bar(x=x_vals, y=y_vals, marker_color=NAVY_BAR, name=block.title))
        if block.show_trend and len(x_vals) >= 2:
            try:
                x_num = np.arange(len(x_vals), dtype=float)
                y_num = np.asarray(y_vals, dtype=float)
                slope, intercept = np.polyfit(x_num, y_num, 1)
                trend_y = slope * x_num + intercept
                fig.add_trace(go.Scatter(
                    x=x_vals, y=trend_y, mode="lines",
                    line=dict(color=COLORS["text_secondary"], width=1.6, dash="dash"),
                    name="Trend", hovertemplate="%{y:.1f}<extra>Trend</extra>",
                ))
            except (TypeError, ValueError):
                pass
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

    elif block.chart_kind == "line":
        # Single-series line — accept both quarterly long (one company) and simple-series schemas
        df_q, meta_q = static_loader.load_quarterly_long(block.yaml_file)
        if not df_q.empty:
            df, meta = df_q, meta_q
        else:
            df, meta = static_loader.load_simple_series(block.yaml_file)
        if df.empty:
            _empty_caption(f"Static file empty or missing: data/static/{block.yaml_file}")
            return
        x_vals, y_vals = df["period"], df["value"]
        line_kw = dict(color=COLORS["accent"], width=2.2)
        if getattr(block, "smooth", False):
            # Gentle spline so the year-to-year line reads less jagged; markers stay on
            # the actual data points.
            line_kw.update(shape="spline", smoothing=1.0)
        fig = go.Figure(go.Scatter(
            x=x_vals, y=y_vals, mode="lines+markers",
            line=line_kw,
            marker=dict(size=5, color=COLORS["accent"]),
            name=block.title, hovertemplate="%{x}: %{y}<extra></extra>",
        ))
        if block.show_trend and len(x_vals) >= 2:
            try:
                x_num = np.arange(len(x_vals), dtype=float)
                y_num = np.asarray(y_vals, dtype=float)
                slope, intercept = np.polyfit(x_num, y_num, 1)
                trend_y = slope * x_num + intercept
                fig.add_trace(go.Scatter(
                    x=x_vals, y=trend_y, mode="lines",
                    line=dict(color=COLORS["text_secondary"], width=1.6, dash="dash"),
                    name="Trend", hovertemplate="%{y:.1f}<extra>Trend</extra>",
                ))
            except (TypeError, ValueError):
                pass
        fig.update_layout(
            height=280, margin=dict(l=10, r=20, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
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
# Advertising-spend peer groups (live from SEC EDGAR, USD)
# ---------------------------------------------------------------------------

def render_ad_groups(groups: list):
    """Render one grouped-bar chart per AdGroup: annual advertising expense (USD bn) by company."""
    for group in groups:
        section_header(group.title)
        frames = []
        for m in group.members:
            ad = data_loader.fetch_advertising_usd(m.ticker)  # {fiscal_year:int -> usd_value:float}
            if not ad:
                continue
            for yr, val in ad.items():
                frames.append({"year": int(yr), "company": m.name, "value": val / 1e9})
        if not frames:
            _empty_caption("Advertising data unavailable — SEC EDGAR could not be reached.")
            continue
        df = pd.DataFrame(frames).sort_values("year")
        years = sorted(df["year"].unique())
        # Preserve config order for the legend / colour assignment
        order = [m.name for m in group.members if m.name in set(df["company"])]

        fig = go.Figure()
        for i, comp in enumerate(order):
            sub = df[df["company"] == comp].set_index("year").reindex(years)
            fig.add_trace(go.Bar(
                x=[str(y) for y in years], y=sub["value"], name=comp,
                marker_color=NAVY_PALETTE[i % len(NAVY_PALETTE)],
                hovertemplate=comp + " %{x}: $%{y:.2f}B<extra></extra>",
            ))
        fig.update_layout(
            height=320, margin=dict(l=10, r=20, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            barmode="group", bargap=0.2,
            xaxis=dict(tickfont=dict(color=COLORS["text_secondary"], size=10)),
            yaxis=dict(
                showgrid=True, gridcolor=COLORS["border"],
                tickfont=dict(color=COLORS["text_secondary"], size=10),
                title=dict(text="Advertising spend (USD bn)", font=dict(size=10, color=COLORS["text_secondary"])),
            ),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, font=dict(size=10)),
        )
        st.plotly_chart(fig, use_container_width=True)
        if group.caption:
            st.caption(group.caption)


# ---------------------------------------------------------------------------
# Quarterly capex charts (live from SEC EDGAR, optional static overlay)
# ---------------------------------------------------------------------------

def _q_sort_key(q: str):
    return (int(q[:4]), int(q[5:]))


def render_capex_chart(chart):
    """Grouped-bar of quarterly capex (USD bn) by calendar quarter, live from EDGAR."""
    section_header(chart.title)
    frames = []
    companies = []
    for m in chart.members:
        q = data_loader.fetch_quarterly_capex(m.ticker)  # {calendar_quarter -> usd}
        if q:
            companies.append(m.name)
        for cq, v in q.items():
            frames.append({"period": cq, "company": m.name, "value": v / 1e9})

    # Optional static overlay for series EDGAR can't supply (e.g. Nebius 20-F filer)
    if chart.static_yaml and chart.static_series:
        sdf, _ = static_loader.load_quarterly_long(chart.static_yaml)
        keymap = dict(chart.static_series)
        for _, row in sdf.iterrows():
            if row["company"] in keymap:
                disp = keymap[row["company"]]
                if disp not in companies:
                    companies.append(disp)
                frames.append({"period": row["period"], "company": disp, "value": row["value"]})

    if not frames:
        _empty_caption("Capex data unavailable — SEC EDGAR could not be reached.")
        return

    df = pd.DataFrame(frames)
    quarters = sorted(df["period"].unique(), key=_q_sort_key)[-12:]   # last ~3 years
    df = df[df["period"].isin(quarters)]
    companies = [c for c in companies if c in set(df["company"])]

    fig = go.Figure()
    for i, comp in enumerate(companies):
        sub = df[df["company"] == comp].set_index("period").reindex(quarters)
        fig.add_trace(go.Bar(
            x=quarters, y=sub["value"], name=comp,
            marker_color=NAVY_PALETTE[i % len(NAVY_PALETTE)],
            hovertemplate=comp + " %{x}: $%{y:.2f}B<extra></extra>",
        ))
    fig.update_layout(
        height=320, margin=dict(l=10, r=20, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        barmode="group", bargap=0.2,
        xaxis=dict(tickfont=dict(color=COLORS["text_secondary"], size=10)),
        yaxis=dict(
            showgrid=True, gridcolor=COLORS["border"],
            tickfont=dict(color=COLORS["text_secondary"], size=10),
            title=dict(text="Capex (USD bn)", font=dict(size=10, color=COLORS["text_secondary"])),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, font=dict(size=10)),
    )
    st.plotly_chart(fig, use_container_width=True)
    if chart.caption:
        st.caption(chart.caption)


