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
# Load logo as base64 (try PNG first for quality)
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
# CSS — mobile responsive
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

    .stApp { background-color: #F8FAFC; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1000px; }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    header[data-testid="stHeader"] { background: #F8FAFC; }

    .home-header {
        display: flex; flex-direction: column; align-items: center;
        padding: 2rem 0 1rem 0; text-align: center; width: 100%;
    }
    .home-logo-wrap {
        display: flex; justify-content: center; width: 100%; margin-bottom: 0.8rem;
    }
    .home-logo-wrap img { height: 300px; display: block; }
    .home-subtitle {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.95rem; color: #64748B;
    }

    .nav-grid {
        display: flex; gap: 1.5rem; justify-content: center;
        margin-top: 2.5rem; flex-wrap: wrap;
    }

    .nav-card {
        position: relative; overflow: hidden;
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;
        width: 400px; min-height: 220px;
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
        height: 100%; padding: 2rem 1.5rem;
        text-align: center;
    }

    .nav-card-title {
        font-family: 'DM Sans', sans-serif;
        font-size: 1.2rem; font-weight: 700; color: #1E293B;
        margin-bottom: 0.6rem; text-decoration: none !important;
    }
    .nav-card-desc {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.8rem; color: #64748B; line-height: 1.5;
        text-decoration: none !important; max-width: 300px;
    }

    a.nav-card, a.nav-card:hover, a.nav-card:visited, a.nav-card:active,
    a.nav-card *, a.nav-card:hover * { text-decoration: none !important; }

    .home-footer {
        text-align: center; font-family: 'DM Sans', sans-serif;
        font-size: 0.7rem; color: #94A3B8; margin-top: 4rem;
        padding-top: 1.5rem; border-top: 1px solid #E2E8F0;
    }

    /* ── Mobile responsive ── */
    @media (max-width: 768px) {
        .block-container { padding-top: 1rem; padding-left: 1rem; padding-right: 1rem; }
        .home-header { padding: 1rem 0 0.5rem 0; }
        .home-logo-wrap img { height: 280px; }
        .home-subtitle { font-size: 0.82rem; }
        .nav-grid { flex-direction: column; align-items: center; gap: 1rem; margin-top: 1.5rem; }
        .nav-card { width: 100%; max-width: 400px; min-height: 180px; }
        .nav-card-content { padding: 1.5rem 1.2rem; }
        .nav-card-title { font-size: 1.05rem; }
        .nav-card-desc { font-size: 0.75rem; }
        .home-footer { margin-top: 2rem; font-size: 0.65rem; }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Card backgrounds
# ---------------------------------------------------------------------------

market_bg_css = """background: repeating-linear-gradient(90deg, #E2E8F0 0px, #E2E8F0 1px, transparent 1px, transparent 60px), repeating-linear-gradient(0deg, #E2E8F0 0px, #E2E8F0 1px, transparent 1px, transparent 40px), linear-gradient(135deg, #EFF6FF 0%, #F8FAFC 100%);"""

portfolio_bg_css = """background: radial-gradient(circle at 30% 50%, rgba(37,99,235,0.08) 0%, transparent 50%), radial-gradient(circle at 70% 40%, rgba(124,58,237,0.06) 0%, transparent 40%), radial-gradient(circle at 50% 70%, rgba(5,150,105,0.05) 0%, transparent 45%), linear-gradient(135deg, #EFF6FF 0%, #F8FAFC 100%);"""

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

logo_img = ""
if logo_b64:
    logo_img = f'<div class="home-logo-wrap"><img src="data:{logo_mime};base64,{logo_b64}" /></div>'

st.markdown(f"""<div class="home-header">{logo_img}<div class="home-subtitle">Investment Intelligence Platform</div></div>""", unsafe_allow_html=True)

st.markdown(f"""<div class="nav-grid"><a class="nav-card" href="/Market_Dashboard" target="_self"><div class="nav-card-bg" style="{market_bg_css}"></div><div class="nav-card-overlay"></div><div class="nav-card-content"><div class="nav-card-title">MARKET DASHBOARD</div><div class="nav-card-desc">Daily macro and market snapshot. Rates, equities, commodities, credit spreads, currencies, and volatility.</div></div></a><a class="nav-card" href="/Portfolio_Dashboard" target="_self"><div class="nav-card-bg" style="{portfolio_bg_css}"></div><div class="nav-card-overlay"></div><div class="nav-card-content"><div class="nav-card-title">PORTFOLIO DASHBOARD</div><div class="nav-card-desc">Current investment allocations by geography, asset class, sector, and stage. Identify gaps and inform strategy.</div></div></a></div>""", unsafe_allow_html=True)

st.markdown("""<div class="home-footer">Secco Capital \u00b7 Investment Intelligence Platform \u00b7 Confidential</div>""", unsafe_allow_html=True)
