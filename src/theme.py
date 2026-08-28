"""
theme.py — light / dark theming for the whole platform.

Streamlit cannot switch the `[theme]` block in .streamlit/config.toml at runtime,
so the app themes itself: every page paints its own surfaces from a palette that
this module publishes as CSS custom properties (`--tk-*`) on the Streamlit
document. Page stylesheets reference the variables rather than hex literals, so a
single palette swap re-skins everything.

How the choice travels
----------------------
The only toggle lives in the home-page topbar (inside app.py's component iframe).
Clicking it writes `secco-theme` to browser localStorage and reloads the top
window with `?theme=<choice>`.

Each page then resolves the theme in this order:

  1. `?theme=` in the URL          — set by the toggle, and carried on the home
                                     page's carousel links (which open in a new
                                     tab, i.e. a fresh session, so session_state
                                     alone would not survive the hop).
  2. `st.session_state`            — keeps the choice across in-session reruns
                                     and sidebar navigation, which drops query
                                     params.
  3. localStorage, via `_storage_bridge()` — a zero-height component iframe whose
                                     JS compares the remembered value against
                                     what the page actually rendered and, on a
                                     mismatch, re-navigates the top window with
                                     the right `?theme=`. This is what makes the
                                     choice survive closing the browser.

The bridge works because Streamlit's component iframes are sandboxed with
`allow-same-origin`, so they share the parent's origin and therefore its
localStorage. Every access is still wrapped in try/except in case that changes.
"""

from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

from src import viz_helpers

DEFAULT_THEME = "light"
QUERY_KEY = "theme"
STATE_KEY = "secco_theme"
STORAGE_KEY = "secco-theme"

# ---------------------------------------------------------------------------
# Palettes
#
# Hyphenated keys are emitted as CSS custom properties with a `--tk-` prefix
# (`text-muted` -> `--tk-text-muted`). The keys named in PLOTLY_ONLY below are
# consumed from Python only and are never emitted as CSS.
# ---------------------------------------------------------------------------

LIGHT = {
    # Surfaces
    "app-bg": "#F8FAFC",
    "surface": "#FFFFFF",
    "surface-alt": "#F1F5F9",
    "surface-sunken": "#F8FAFC",
    # Lines
    "border": "#E2E8F0",
    "border-soft": "#F1F5F9",
    "border-strong": "#CBD5E1",
    # Type
    "text": "#1E293B",
    "text-strong": "#0F172A",
    "text-soft": "#475569",
    "text-muted": "#64748B",
    "text-faint": "#94A3B8",
    # Accent
    "accent": "#4F7FD6",
    "accent-glow": "rgba(79,127,214,0.24)",
    "on-accent": "#FFFFFF",
    # Signal
    "pos": "#16A34A",
    "pos-strong": "#15803D",
    "neg": "#DC2626",
    "warn": "#F59E0B",
    "callout-pos-bg": "rgba(22,163,74,0.05)",
    "callout-neg-bg": "rgba(220,38,38,0.04)",
    "flash-pos": "rgba(22,163,74,0.14)",
    "flash-neg": "rgba(220,38,38,0.12)",
    # Charts
    "grid": "#E2E8F0",
    "chart-1": "#A9B6C6",
    "chart-2": "#C3CDD9",
    "chart-3": "#D3DBE4",
    # Tooltips
    "tooltip-bg": "#1E293B",
    "tooltip-text": "#F8FAFC",
    "tooltip-strong": "#FFFFFF",
    # Shadows
    "shadow-sm": "rgba(15,23,42,0.05)",
    "shadow-md": "rgba(15,23,42,0.10)",
    "shadow-lg": "rgba(15,23,42,0.15)",
    # Tags / chips
    "tag-bg": "#F1F5F9",
    "tag-border": "#E2E8F0",
    "tag-text": "#334155",
    "tag-pos-bg": "#DCFCE7",
    "tag-pos-border": "#BBF7D0",
    "tag-pos-text": "#166534",
    "tag-warn-bg": "#FEF3C7",
    "tag-warn-border": "#FDE68A",
    "tag-warn-text": "#92400E",
    # Geo map
    "map-land": "#F1F5F9",
    "map-ocean": "#EFF6FF",
    "map-line": "#CBD5E1",
    "map-frame": "#E2E8F0",
    # Home page composites
    "home-bg": (
        "radial-gradient(1200px 520px at 50% -180px, rgba(79,127,214,0.10),"
        " rgba(79,127,214,0) 70%),"
        " linear-gradient(180deg,#FFFFFF 0%,#F8FAFC 55%,#F1F5F9 100%)"
    ),
    "home-bar-bg": "rgba(255,255,255,0.72)",
    "logo-filter": "none",
    "home-ticker-bg": "linear-gradient(180deg,#FFFFFF,#FBFCFE)",
    # Plotly-only sequences (not emitted as CSS)
    "choropleth": ["#DBEAFE", "#93C5FD", "#3B82F6", "#1E3A8A"],
    "categorical": ["#4F7FD6", "#16A34A", "#F59E0B", "#EC4899",
                    "#14B8A6", "#6366F1", "#DC2626", "#0EA5E9"],
    "navy_scale": ["#0A2A4A", "#15528A", "#2E7BC4", "#5BA0DA", "#93C0EA", "#C7DEF4"],
    "navy_bar": "#15528A",
    "muted_series": ["#94A3B8", "#6366F1", "#F59E0B", "#14B8A6", "#EC4899"],
    "partner_bars": {"geo": "#4F7FD6", "asset_class": "#7C3AED",
                     "sector": "#0891B2", "stage": "#059669"},
}

DARK = {
    # Surfaces
    "app-bg": "#0B1220",
    "surface": "#111C2E",
    "surface-alt": "#1A2740",
    "surface-sunken": "#0E1828",
    # Lines
    "border": "#26344E",
    "border-soft": "#1E2B44",
    "border-strong": "#3A4A68",
    # Type
    "text": "#DBE3EE",
    "text-strong": "#F1F5F9",
    "text-soft": "#B3C0D4",
    "text-muted": "#93A3BA",
    "text-faint": "#7C8DA6",
    # Accent
    "accent": "#6FA0EC",
    "accent-glow": "rgba(111,160,236,0.30)",
    "on-accent": "#06101F",
    # Signal
    "pos": "#34D399",
    "pos-strong": "#6EE7B7",
    "neg": "#F87171",
    "warn": "#FBBF24",
    "callout-pos-bg": "rgba(52,211,153,0.10)",
    "callout-neg-bg": "rgba(248,113,113,0.10)",
    "flash-pos": "rgba(52,211,153,0.18)",
    "flash-neg": "rgba(248,113,113,0.16)",
    # Charts
    "grid": "#26344E",
    "chart-1": "#5A6C86",
    "chart-2": "#46566E",
    "chart-3": "#33415A",
    # Tooltips
    "tooltip-bg": "#24334D",
    "tooltip-text": "#F1F5F9",
    "tooltip-strong": "#FFFFFF",
    # Shadows
    "shadow-sm": "rgba(0,0,0,0.35)",
    "shadow-md": "rgba(0,0,0,0.45)",
    "shadow-lg": "rgba(0,0,0,0.55)",
    # Tags / chips
    "tag-bg": "#1A2740",
    "tag-border": "#26344E",
    "tag-text": "#C3CFE2",
    "tag-pos-bg": "rgba(52,211,153,0.14)",
    "tag-pos-border": "rgba(52,211,153,0.34)",
    "tag-pos-text": "#6EE7B7",
    "tag-warn-bg": "rgba(251,191,36,0.14)",
    "tag-warn-border": "rgba(251,191,36,0.32)",
    "tag-warn-text": "#FCD34D",
    # Geo map
    "map-land": "#1A2740",
    "map-ocean": "#0B1220",
    "map-line": "#3A4A68",
    "map-frame": "#26344E",
    # Home page composites
    "home-bg": (
        "radial-gradient(1200px 520px at 50% -180px, rgba(111,160,236,0.16),"
        " rgba(111,160,236,0) 70%),"
        " linear-gradient(180deg,#0B1220 0%,#0D1626 55%,#101C30 100%)"
    ),
    "home-bar-bg": "rgba(11,18,32,0.72)",
    "logo-filter": "brightness(0) invert(1) opacity(0.86)",
    "home-ticker-bg": "linear-gradient(180deg,#101A2C,#0C1524)",
    # Plotly-only sequences
    "choropleth": ["#152C4E", "#1E4A85", "#2E6FC4", "#7FB2F0"],
    "categorical": ["#6FA0EC", "#34D399", "#FBBF24", "#F472B6",
                    "#2DD4BF", "#818CF8", "#F87171", "#38BDF8"],
    "navy_scale": ["#7FB2F0", "#5B92DE", "#3E72BE", "#2C5694", "#1E3E6E", "#152C4E"],
    "navy_bar": "#4C86D4",
    "muted_series": ["#7C8DA6", "#818CF8", "#FBBF24", "#2DD4BF", "#F472B6"],
    "partner_bars": {"geo": "#6FA0EC", "asset_class": "#A78BFA",
                     "sector": "#22D3EE", "stage": "#34D399"},
}

PALETTES = {"light": LIGHT, "dark": DARK}

# Palette entries that exist for Plotly's benefit and have no CSS counterpart.
PLOTLY_ONLY = frozenset({
    "choropleth", "categorical", "navy_scale", "navy_bar",
    "muted_series", "partner_bars",
})


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def resolve_theme() -> str:
    """Return the theme this page should render in, and remember it for the
    rest of the session. Query param wins over session_state so the home-page
    toggle and the carousel's new-tab links are always authoritative."""
    try:
        requested = st.query_params.get(QUERY_KEY)
    except Exception:
        requested = None
    if isinstance(requested, list):
        requested = requested[0] if requested else None
    if requested in PALETTES:
        st.session_state[STATE_KEY] = requested
        return requested
    return st.session_state.get(STATE_KEY, DEFAULT_THEME)


def palette(theme: str | None = None) -> dict:
    """The active palette dict. Values are CSS colour strings, except the
    Plotly-only sequence keys (`categorical`, `navy_scale`, …)."""
    return PALETTES[theme or resolve_theme()]


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def css_variables(theme: str) -> str:
    """`--tk-*` declarations for the given theme, without the wrapping block."""
    p = PALETTES[theme]
    return "".join(
        f"--tk-{k}:{v};" for k, v in p.items() if k not in PLOTLY_ONLY
    )


def _chrome_css(theme: str) -> str:
    """Restyle the Streamlit widgets the app does not paint itself.

    config.toml pins Streamlit's own theme to light so tables and menus stay
    legible there; in dark mode those defaults have to be overridden by hand.
    `!important` is unavoidable — Streamlit's emotion classes are more specific
    than anything we can write."""
    if theme != "dark":
        return ""
    return """
    /* ── Shell ── */
    .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stMain"], [data-testid="stBottomBlockContainer"] {
        background-color: var(--tk-app-bg) !important;
        color: var(--tk-text) !important;
    }
    header[data-testid="stHeader"] { background: var(--tk-app-bg) !important; }
    [data-testid="stToolbar"], [data-testid="stStatusWidget"] { color: var(--tk-text-muted) !important; }
    [data-testid="stDecoration"] { display: none !important; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"], [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"] {
        background-color: var(--tk-surface) !important;
        border-right: 1px solid var(--tk-border);
    }
    [data-testid="stSidebar"] * { color: var(--tk-text) !important; }
    [data-testid="stSidebarNav"] a { color: var(--tk-text-muted) !important; }
    [data-testid="stSidebarNav"] a:hover { background: var(--tk-surface-alt) !important; }
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stSidebarCollapsedControl"] svg { fill: var(--tk-text-muted) !important; }

    /* ── Type ── */
    body, p, li, span, label, h1, h2, h3, h4, h5, h6 { color: var(--tk-text); }
    [data-testid="stMarkdownContainer"] { color: var(--tk-text); }
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
        color: var(--tk-text-muted) !important;
    }
    a { color: var(--tk-accent); }
    hr, [data-testid="stDivider"] hr { border-color: var(--tk-border) !important; }
    code, [data-testid="stCode"] {
        background: var(--tk-surface-alt) !important;
        color: var(--tk-text-strong) !important;
    }

    /* ── Inputs ── */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {
        background: var(--tk-surface) !important;
        color: var(--tk-text) !important;
        border-color: var(--tk-border) !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: var(--tk-text-faint) !important;
    }
    [data-baseweb="select"] > div, [data-baseweb="input"] {
        background: var(--tk-surface) !important;
        border-color: var(--tk-border) !important;
        color: var(--tk-text) !important;
    }
    [data-baseweb="popover"] [role="listbox"], [data-baseweb="menu"], [data-baseweb="list"] {
        background: var(--tk-surface) !important;
        color: var(--tk-text) !important;
        border: 1px solid var(--tk-border) !important;
    }
    [data-baseweb="menu"] li:hover, [role="option"]:hover {
        background: var(--tk-surface-alt) !important;
    }
    [data-baseweb="tag"] {
        background: var(--tk-accent) !important;
        color: var(--tk-on-accent) !important;
    }
    [data-baseweb="tag"] svg { fill: var(--tk-on-accent) !important; }

    /* ── Radio / checkbox / toggle ── */
    [data-testid="stRadio"] label, [data-testid="stCheckbox"] label {
        color: var(--tk-text) !important;
    }
    [data-testid="stWidgetLabel"] p { color: var(--tk-text-muted) !important; }

    /* ── Expander & popover ── */
    [data-testid="stExpander"] details {
        background: var(--tk-surface) !important;
        border-color: var(--tk-border) !important;
    }
    [data-testid="stExpander"] summary { color: var(--tk-text) !important; }
    [data-testid="stPopoverBody"] {
        background: var(--tk-surface) !important;
        border: 1px solid var(--tk-border) !important;
    }
    [data-testid="stTooltipContent"] {
        background: var(--tk-tooltip-bg) !important;
        color: var(--tk-tooltip-text) !important;
    }

    /* ── Alerts & spinner ── */
    [data-testid="stNotification"], [data-testid="stAlert"] {
        background: var(--tk-surface-alt) !important;
        color: var(--tk-text) !important;
    }
    [data-testid="stSpinner"] { color: var(--tk-text-muted) !important; }

    /* ── Dataframes (none today, but keep them legible if one is added) ── */
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        background: var(--tk-surface) !important;
        color: var(--tk-text) !important;
    }
    """


def _shared_css(theme: str) -> str:
    """Rules every page wants, regardless of theme."""
    return f"""
    :root {{ {css_variables(theme)} }}
    /* The localStorage bridge is a component iframe with no visible content.
       Hide the marker element and the component that follows it so neither
       reserves vertical space. A display:none iframe still loads and runs its
       script, which is all the bridge needs. */
    [data-testid="stElementContainer"]:has(> .stMarkdown .secco-theme-bridge),
    [data-testid="stElementContainer"]:has(> .stMarkdown .secco-theme-bridge)
        + [data-testid="stElementContainer"] {{
        display: none !important;
    }}
    /* Fallback for browsers without :has() support. */
    iframe[height="0"] {{ display: none !important; height: 0 !important; }}
    .secco-theme-bridge {{ display: none; }}
    """


# ---------------------------------------------------------------------------
# Shared page stylesheet
#
# Every dashboard page used to carry its own copy of the block below — the same
# font import, shell, chrome-hiding and button rules, plus a header family that
# differed only by class prefix (.port-, .watch-, .di-, .am-). One copy lives
# here now and the pages call page_css().
#
# What is deliberately NOT here: the per-page data tables. They look alike but
# differ in font size, cell padding and column alignment (the Partner table is
# left-aligned throughout, Alt Managers adds nowrap and .txt columns), so a
# shared base would need so many overrides that each page is clearer owning its
# own. Same for genuinely page-specific components — metric cards, KPI cards,
# holding callouts, tooltips.
#
# `__MAXW__` is substituted rather than using an f-string so the CSS braces do
# not have to be doubled throughout.
# ---------------------------------------------------------------------------

_PAGE_CSS = """
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

    /* ── Shell ── */
    .stApp { background-color: var(--tk-app-bg); color: var(--tk-text); }
    .block-container { padding-top: 2rem; padding-bottom: 1rem; max-width: __MAXW__; }

    /* ── Hide Streamlit's own chrome ── */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    header[data-testid="stHeader"] { background: var(--tk-app-bg); }
    .stPlotlyChart { background: transparent !important; }

    /* ── Page header ── */
    .page-header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.75rem 0 1.25rem 0; border-bottom: 1px solid var(--tk-border);
        margin-bottom: 1.5rem;
    }
    .page-header-left { display: flex; align-items: center; gap: 0.75rem; }
    .page-logo {
        height: 36px; width: auto;
        /* The wordmark is a single flat slate; on a dark ground it has to be
           inverted to stay legible. No-op in the light theme. */
        filter: var(--tk-logo-filter);
    }
    .page-title {
        font-family: 'DM Sans', sans-serif; font-size: 1.4rem;
        font-weight: 700; color: var(--tk-text); letter-spacing: -0.02em;
    }
    .page-subtitle {
        font-family: 'DM Sans', sans-serif; font-size: 0.8rem;
        color: var(--tk-text-muted); margin-top: 2px;
    }
    .page-timestamp {
        font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
        color: var(--tk-text-muted); text-align: right;
    }

    /* ── Section header ──
       Direct Investments and Alt Managers want roomier spacing and override
       the padding / margin-bottom locally. */
    .section-header {
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600;
        color: var(--tk-text-muted); text-transform: uppercase; letter-spacing: 0.12em;
        padding: 0.6rem 0 0.4rem 0; border-bottom: 1px solid var(--tk-border);
        margin-bottom: 0.6rem;
    }

    /* ── Shared inline bits ── */
    .stock-ticker {
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
        color: var(--tk-text-faint); margin-left: 0.4rem;
    }
    .chg-up { color: var(--tk-pos); }
    .chg-down { color: var(--tk-neg); }
    .chg-flat { color: var(--tk-text-muted); }

    /* ── Buttons ── */
    .stButton > button {
        background: var(--tk-surface); color: var(--tk-text);
        border: 1px solid var(--tk-border-strong);
        font-family: 'DM Sans', sans-serif; font-size: 0.78rem; font-weight: 600;
        border-radius: 4px; padding: 0.4rem 1.2rem;
    }
    .stButton > button:hover {
        background: var(--tk-surface-alt); border-color: var(--tk-accent);
        color: var(--tk-text);
    }

    /* ── Mobile ── */
    @media (max-width: 768px) {
        .block-container { padding-left: 0.5rem; padding-right: 0.5rem; max-width: 100%; }
        .page-header { flex-direction: column; gap: 0.5rem; }
        .page-title { font-size: 1.1rem; }
        .section-header { font-size: 0.6rem; }
    }
"""


def page_css(max_width: str = "1400px") -> str:
    """The stylesheet every dashboard page shares, as the inner text of a
    `<style>` block. Pass the page's content width; everything else is fixed.

    Emit it before the page's own rules so those win on equal specificity:

        st.markdown(f"<style>{page_css()}\\n.my-rule {{...}}</style>", ...)
    """
    return _PAGE_CSS.replace("__MAXW__", max_width)


# ---------------------------------------------------------------------------
# localStorage bridge
# ---------------------------------------------------------------------------

_BRIDGE = """
<script>
(function () {
  var KEY = %s, applied = %s;
  function store() {
    try { return window.top.localStorage; } catch (e) {}
    try { return window.localStorage; } catch (e) {}
    return null;
  }
  var ls = store();
  if (!ls) return;
  var remembered = null;
  try { remembered = ls.getItem(KEY); } catch (e) { return; }
  if (!remembered || remembered === applied) return;
  if (remembered !== 'light' && remembered !== 'dark') return;
  try {
    var win = window.top || window.parent;
    var url = new URL(win.location.href);
    // Guard against a redirect loop: if the URL already asks for the remembered
    // theme, the mismatch is not something another navigation can fix.
    if (url.searchParams.get('theme') === remembered) return;
    url.searchParams.set('theme', remembered);
    // Paint the parent immediately so the wrong theme does not flash while the
    // replacement page loads.
    win.document.documentElement.style.background =
      remembered === 'dark' ? '#0B1220' : '#F8FAFC';
    win.location.replace(url.toString());
  } catch (e) {}
})();
</script>
"""


def _storage_bridge(theme: str) -> None:
    # The marker gives _shared_css a stable hook for collapsing the iframe that
    # follows it, without depending on how Streamlit renders the height attribute.
    st.markdown('<div class="secco-theme-bridge"></div>', unsafe_allow_html=True)
    components.html(
        _BRIDGE % (json.dumps(STORAGE_KEY), json.dumps(theme)),
        height=0,
    )


def storage_writer_js() -> str:
    """JS for the home-page toggle: remember the choice, then reload the top
    window under the new theme. Returned as a string because the toggle lives
    inside app.py's own component iframe."""
    return """
  function seccoSetTheme(t) {
    var KEY = %s;
    try { window.top.localStorage.setItem(KEY, t); }
    catch (e) { try { window.localStorage.setItem(KEY, t); } catch (e2) {} }
    try {
      var win = window.top || window.parent;
      var url = new URL(win.location.href);
      url.searchParams.set('theme', t);
      win.document.documentElement.style.background =
        t === 'dark' ? '#0B1220' : '#F8FAFC';
      win.location.replace(url.toString());
    } catch (e) { location.reload(); }
  }
""" % json.dumps(STORAGE_KEY)


# ---------------------------------------------------------------------------
# Plotly / helper synchronisation
# ---------------------------------------------------------------------------

def _sync_viz_colors(theme: str) -> None:
    """Point `viz_helpers.COLORS` at the active palette.

    Mutated in place, never rebound: `src/direct_investments/views.py` imports
    the dict by name, so rebinding here would leave that module on the old
    palette."""
    p = PALETTES[theme]
    viz_helpers.COLORS.update({
        "green": p["pos"],
        "red": p["neg"],
        "neutral": p["text-faint"],
        "bg_dark": p["app-bg"],
        "bg_card": p["surface"],
        "bg_card_alt": p["surface-alt"],
        "text_primary": p["text"],
        "text_secondary": p["text-muted"],
        "border": p["grid"],
        "accent": p["accent"],
    })


def plotly_layout(theme: str | None = None, **overrides) -> dict:
    """Transparent-background layout defaults with theme-correct fonts and
    gridlines. Pass to `fig.update_layout(**plotly_layout())`."""
    p = palette(theme)
    base = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": p["text"]},
        "hoverlabel": {
            "bgcolor": p["tooltip-bg"],
            "font": {"color": p["tooltip-text"]},
            "bordercolor": p["border"],
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def apply_theme() -> str:
    """Resolve the theme, publish its CSS variables, restyle Streamlit's own
    widgets, and start the localStorage bridge. Call once per page, immediately
    after `st.set_page_config`. Returns the active theme name."""
    theme = resolve_theme()
    _sync_viz_colors(theme)
    st.markdown(
        f"<style>{_shared_css(theme)}{_chrome_css(theme)}</style>",
        unsafe_allow_html=True,
    )
    _storage_bridge(theme)
    return theme
