"""
app.py — Secco Capital Platform Home Page
"""

import base64
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Secco Capital",
    page_icon="◼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Load logo as base64 (try PNG first, then SVG)
# ---------------------------------------------------------------------------

logo_b64 = ""
logo_mime = ""
root = Path(__file__).parent
for name, mime in [("logo.png", "image/png"), ("logo.svg", "image/svg+xml"), ("Secco_logo.png", "image/png"), ("Secco_logo.svg", "image/svg+xml")]:
    p = root / name
    if p.exists():
        logo_b64 = base64.b64encode(p.read_bytes()).decode()
        logo_mime = mime
        break

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

    .stApp { background-color: #F8FAFC; }
    .block-container { padding-top: 3rem; padding-bottom: 2rem; max-width: 1000px; }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    header[data-testid="stHeader"] { background: #F8FAFC; }

    .home-header { text-align: center; padding: 2rem 0 1rem 0; }
    .home-subtitle {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.95rem; color: #64748B;
    }

    .nav-grid {
        display: flex; gap: 1.5rem; justify-content: center;
        margin-top: 2.5rem; flex-wrap: nowrap;
    }

    .nav-card {
        position: relative; overflow: hidden;
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;
        width: 400px; height: 260px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
        text-decoration: none !important; display: block;
    }
    .nav-card:hover {
        border-color: #2563EB; box-shadow: 0 4px 12px rgba(37,99,235,0.12);
        transform: translateY(-2px);
    }

    .nav-card-bg {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        opacity: 0.08;
    }

    .nav-card-overlay {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: linear-gradient(180deg, rgba(248,250,252,0.3) 0%, rgba(255,255,255,0.92) 55%);
    }

    .nav-card-content {
        position: relative; z-index: 1;
        display: flex; flex-direction: column;
        justify-content: center; align-items: center;
        height: 100%; padding: 1.5rem 2rem;
        text-align: center;
    }

    .nav-card-title {
        font-family: 'DM Sans', sans-serif;
        font-size: 1.2rem; font-weight: 700; color: #1E293B;
        margin-bottom: 0.6rem;
        text-decoration: none !important;
    }
    .nav-card-desc {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.8rem; color: #64748B; line-height: 1.5;
        text-decoration: none !important;
        max-width: 300px;
    }

    a.nav-card, a.nav-card:hover, a.nav-card:visited, a.nav-card:active,
    a.nav-card *, a.nav-card:hover * {
        text-decoration: none !important;
    }

    .home-footer {
        text-align: center; font-family: 'DM Sans', sans-serif;
        font-size: 0.7rem; color: #94A3B8; margin-top: 4rem;
        padding-top: 1.5rem; border-top: 1px solid #E2E8F0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Card background patterns (pure CSS, no SVG embedding)
# ---------------------------------------------------------------------------

market_bg_css = """
    background:
        repeating-linear-gradient(90deg, #E2E8F0 0px, #E2E8F0 1px, transparent 1px, transparent 60px),
        repeating-linear-gradient(0deg, #E2E8F0 0px, #E2E8F0 1px, transparent 1px, transparent 40px),
        linear-gradient(135deg, #EFF6FF 0%, #F8FAFC 100%);
"""

portfolio_bg_css = """
    background:
        radial-gradient(circle at 30% 50%, rgba(37,99,235,0.08) 0%, transparent 50%),
        radial-gradient(circle at 70% 40%, rgba(124,58,237,0.06) 0%, transparent 40%),
        radial-gradient(circle at 50% 70%, rgba(5,150,105,0.05) 0%, transparent 45%),
        linear-gradient(135deg, #EFF6FF 0%, #F8FAFC 100%);
"""

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

logo_img = ""
if logo_b64:
    logo_img = f'<img src="data:{logo_mime};base64,{logo_b64}" style="height:300px; margin:0.8rem auto;" />'

st.markdown(f"""<div class="home-header">{logo_img}<div class="home-subtitle">Investment Intelligence Platform</div></div>""", unsafe_allow_html=True)

st.markdown(f"""<div class="nav-grid"><a class="nav-card" href="/Market_Dashboard" target="_self"><div class="nav-card-bg" style="{market_bg_css}"></div><div class="nav-card-overlay"></div><div class="nav-card-content"><div class="nav-card-title">Market Dashboard</div><div class="nav-card-desc">Daily macro and market snapshot. Rates, equities, commodities, credit spreads, currencies, and volatility.</div></div></a><a class="nav-card" href="/Portfolio_Dashboard" target="_self"><div class="nav-card-bg" style="{portfolio_bg_css}"></div><div class="nav-card-overlay"></div><div class="nav-card-content"><div class="nav-card-title">Portfolio Dashboard</div><div class="nav-card-desc">Current investment allocations by geography, asset class, sector, and stage. Identify gaps and inform strategy.</div></div></a></div>""", unsafe_allow_html=True)

st.markdown("""<div class="home-footer">Secco Capital · Investment Intelligence Platform · Confidential</div>""", unsafe_allow_html=True)
