"""
viz_helpers.py — Visualisation utilities.
Formatting functions, colour logic, and Plotly chart builders
used by the Streamlit dashboard.
"""

import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Colour scheme — institutional palette
# ---------------------------------------------------------------------------

COLORS = {
    "green": "#16A34A",
    "red": "#DC2626",
    "neutral": "#94A3B8",
    "bg_dark": "#F8FAFC",
    "bg_card": "#FFFFFF",
    "bg_card_alt": "#F1F5F9",
    "text_primary": "#1E293B",
    "text_secondary": "#64748B",
    "border": "#E2E8F0",
    "accent": "#2563EB",
}

# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def fmt_value(val, is_rate=False, is_spread=False) -> str:
    """Format the latest value for display."""
    if val is None:
        return "—"
    if is_rate:
        return f"{val:.2f}%"
    if is_spread:
        return f"{val * 100:.0f} bps"
    if abs(val) >= 1000:
        return f"{val:,.2f}"
    return f"{val:.2f}"


def fmt_change(val, is_rate=False, is_spread=False) -> str:
    """Format a change value with sign."""
    if val is None:
        return "—"
    sign = "+" if val > 0 else ""
    if is_rate:
        return f"{sign}{val:.2f}%"
    if is_spread:
        return f"{sign}{val:.0f} bps"
    return f"{sign}{val:.2f}%"


def change_color(val, invert=False) -> str:
    """Return green/red/neutral hex color based on sign. Invert for VIX/spreads."""
    if val is None or val == 0:
        return COLORS["neutral"]
    positive = val > 0
    if invert:
        positive = not positive
    return COLORS["green"] if positive else COLORS["red"]

# ---------------------------------------------------------------------------
# Sparkline chart
# ---------------------------------------------------------------------------

def make_sparkline(
    df: pd.DataFrame,
    name: str = "",
    days: int = 30,
    invert_color: bool = False,
    height: int = 120,
) -> go.Figure:
    """
    Create a minimal sparkline chart from a Close-price DataFrame.
    Shows the last `days` trading days. Y-axis scaled to data range
    so price movements are clearly visible.
    """
    if df is None or df.empty:
        return _empty_fig(height)

    recent = df.tail(days)
    if recent.empty:
        return _empty_fig(height)

    first_val = float(recent["Close"].iloc[0])
    last_val = float(recent["Close"].iloc[-1])
    is_up = last_val >= first_val
    if invert_color:
        is_up = not is_up
    line_color = COLORS["green"] if is_up else COLORS["red"]

    # Convert hex color to rgba for fill
    hex_c = line_color.lstrip("#")
    r, g, b = int(hex_c[0:2], 16), int(hex_c[2:4], 16), int(hex_c[4:6], 16)
    fill_color = f"rgba({r},{g},{b},0.12)"

    # Y-axis range: tight to data with 10% padding so moves are visible
    y_min = float(recent["Close"].min())
    y_max = float(recent["Close"].max())
    y_pad = (y_max - y_min) * 0.1 if y_max > y_min else y_max * 0.01
    y_range = [y_min - y_pad, y_max + y_pad]

    fig = go.Figure()

    # Baseline trace at the bottom of visible range (for fill reference)
    fig.add_trace(go.Scatter(
        x=recent.index,
        y=[y_range[0]] * len(recent),
        mode="lines",
        line=dict(width=0),
        hoverinfo="skip",
        showlegend=False,
    ))

    # Actual price line with fill down to the baseline
    fig.add_trace(go.Scatter(
        x=recent.index,
        y=recent["Close"],
        mode="lines",
        line=dict(color=line_color, width=1.8),
        fill="tonexty",
        fillcolor=fill_color,
        hoverinfo="skip",
        showlegend=False,
    ))

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=14, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=y_range),
        showlegend=False,
        annotations=[
            # Start date (left)
            dict(
                x=recent.index[0], y=y_range[1],
                text=recent.index[0].strftime("%d %b"),
                showarrow=False, xanchor="left", yanchor="bottom",
                font=dict(size=9, color=COLORS["text_secondary"], family="JetBrains Mono, monospace"),
                yref="y", xref="x",
            ),
            # End date (right)
            dict(
                x=recent.index[-1], y=y_range[1],
                text=recent.index[-1].strftime("%d %b"),
                showarrow=False, xanchor="right", yanchor="bottom",
                font=dict(size=9, color=COLORS["text_secondary"], family="JetBrains Mono, monospace"),
                yref="y", xref="x",
            ),
        ],
    )
    return fig


def make_vix_sparkline(
    df: pd.DataFrame,
    vix_avg: float | None = None,
    days: int = 90,
    height: int = 100,
) -> go.Figure:
    """
    VIX sparkline with a horizontal 1Y average line overlay.
    """
    if df is None or df.empty:
        return _empty_fig(height)

    recent = df.tail(days)
    if recent.empty:
        return _empty_fig(height)

    first_val = float(recent["Close"].iloc[0])
    last_val = float(recent["Close"].iloc[-1])
    # VIX: up = bad (red)
    line_color = COLORS["red"] if last_val >= first_val else COLORS["green"]

    hex_c = line_color.lstrip("#")
    r, g, b = int(hex_c[0:2], 16), int(hex_c[2:4], 16), int(hex_c[4:6], 16)
    fill_color = f"rgba({r},{g},{b},0.12)"

    y_min = float(recent["Close"].min())
    y_max = float(recent["Close"].max())
    # Extend range to fit average line if needed
    if vix_avg is not None:
        y_min = min(y_min, vix_avg)
        y_max = max(y_max, vix_avg)
    y_pad = (y_max - y_min) * 0.1 if y_max > y_min else y_max * 0.01
    y_range = [y_min - y_pad, y_max + y_pad]

    fig = go.Figure()

    # Baseline
    fig.add_trace(go.Scatter(
        x=recent.index, y=[y_range[0]] * len(recent),
        mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False,
    ))

    # VIX line
    fig.add_trace(go.Scatter(
        x=recent.index, y=recent["Close"],
        mode="lines", line=dict(color=line_color, width=1.8),
        fill="tonexty", fillcolor=fill_color,
        hoverinfo="skip", showlegend=False,
    ))

    # 1Y average line
    annotations = []
    if vix_avg is not None:
        fig.add_trace(go.Scatter(
            x=[recent.index[0], recent.index[-1]],
            y=[vix_avg, vix_avg],
            mode="lines",
            line=dict(color=COLORS["accent"], width=1.2, dash="dash"),
            hoverinfo="skip", showlegend=False,
        ))
        annotations.append(dict(
            x=recent.index[-1], y=vix_avg,
            text=f"1Y avg: {vix_avg:.0f}",
            showarrow=False, xanchor="right", yanchor="bottom",
            font=dict(size=8, color=COLORS["accent"], family="JetBrains Mono, monospace"),
            yref="y", xref="x",
        ))

    # Date labels
    annotations.extend([
        dict(
            x=recent.index[0], y=y_range[1],
            text=recent.index[0].strftime("%d %b"),
            showarrow=False, xanchor="left", yanchor="bottom",
            font=dict(size=9, color=COLORS["text_secondary"], family="JetBrains Mono, monospace"),
        ),
        dict(
            x=recent.index[-1], y=y_range[1],
            text=recent.index[-1].strftime("%d %b"),
            showarrow=False, xanchor="right", yanchor="bottom",
            font=dict(size=9, color=COLORS["text_secondary"], family="JetBrains Mono, monospace"),
        ),
    ])

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=14, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=y_range),
        showlegend=False,
        annotations=annotations,
    )
    return fig


def _empty_fig(height: int = 80) -> go.Figure:
    """Return a blank placeholder figure."""
    fig = go.Figure()
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[dict(
            text="No data", x=0.5, y=0.5,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(color=COLORS["text_secondary"], size=10),
        )],
    )
    return fig

# ---------------------------------------------------------------------------
# Bar chart for LTM returns
# ---------------------------------------------------------------------------

def make_ltm_bar_chart(metrics_df: pd.DataFrame, category: str) -> go.Figure:
    """Horizontal bar chart of LTM (last twelve months) changes for a given category."""
    cat_df = metrics_df[metrics_df["category"] == category].copy()
    cat_df = cat_df.dropna(subset=["ltm_chg"])

    if cat_df.empty:
        return _empty_fig(200)

    colors = [
        change_color(row["ltm_chg"], row["invert_color"])
        for _, row in cat_df.iterrows()
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=cat_df.index,
        x=cat_df["ltm_chg"],
        orientation="h",
        marker_color=colors,
        text=[fmt_change(v, row["is_rate"], row["is_spread"]) for v, (_, row) in zip(cat_df["ltm_chg"], cat_df.iterrows())],
        textposition="outside",
        textfont=dict(color=COLORS["text_primary"], size=11),
        cliponaxis=False,
        hoverinfo="skip",
    ))

    # Pad the x-axis so outside labels aren't cut off
    vals = cat_df["ltm_chg"].abs()
    x_max = vals.max() if not vals.empty else 10
    padding = x_max * 0.35

    fig.update_layout(
        height=max(180, 45 * len(cat_df)),
        margin=dict(l=10, r=20, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=True,
            gridcolor=COLORS["border"],
            zeroline=True,
            zerolinecolor=COLORS["text_secondary"],
            zerolinewidth=1,
            tickfont=dict(color=COLORS["text_secondary"], size=10),
            range=[-(vals.max() + padding) if cat_df["ltm_chg"].min() < 0 else 0,
                   x_max + padding],
        ),
        yaxis=dict(
            tickfont=dict(color=COLORS["text_primary"], size=11),
            autorange="reversed",
        ),
        showlegend=False,
        bargap=0.35,
    )
    return fig
