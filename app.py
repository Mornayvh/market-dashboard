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
# Load logo
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
# Preview images as base64 PNGs generated from inline SVG
# ---------------------------------------------------------------------------

market_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><rect width="400" height="200" fill="#F8FAFC"/><rect x="15" y="12" width="58" height="28" rx="3" fill="#E2E8F0"/><rect x="80" y="12" width="58" height="28" rx="3" fill="#E2E8F0"/><rect x="145" y="12" width="58" height="28" rx="3" fill="#E2E8F0"/><rect x="210" y="12" width="58" height="28" rx="3" fill="#E2E8F0"/><rect x="275" y="12" width="58" height="28" rx="3" fill="#E2E8F0"/><rect x="340" y="12" width="46" height="28" rx="3" fill="#E2E8F0"/><rect x="15" y="55" width="175" height="6" rx="2" fill="#CBD5E1"/><rect x="15" y="68" width="175" height="4" rx="1" fill="#E2E8F0"/><rect x="15" y="78" width="175" height="4" rx="1" fill="#E2E8F0"/><rect x="15" y="88" width="175" height="4" rx="1" fill="#E2E8F0"/><rect x="15" y="98" width="175" height="4" rx="1" fill="#E2E8F0"/><rect x="210" y="55" width="175" height="6" rx="2" fill="#CBD5E1"/><rect x="210" y="68" width="175" height="4" rx="1" fill="#E2E8F0"/><rect x="210" y="78" width="175" height="4" rx="1" fill="#E2E8F0"/><rect x="210" y="88" width="175" height="4" rx="1" fill="#E2E8F0"/><rect x="210" y="98" width="175" height="4" rx="1" fill="#E2E8F0"/><rect x="15" y="115" width="175" height="6" rx="2" fill="#CBD5E1"/><rect x="15" y="128" width="175" height="4" rx="1" fill="#E2E8F0"/><rect x="15" y="138" width="175" height="4" rx="1" fill="#E2E8F0"/><polyline points="15,185 55,172 95,176 135,162 175,168 215,155 255,158 295,148 335,153 385,142" fill="none" stroke="#16A34A" stroke-width="2" opacity="0.6"/><polyline points="15,190 55,180 95,184 135,174 175,178 215,170 255,172 295,164 335,168 385,158" fill="none" stroke="#3B82F6" stroke-width="2" opacity="0.4"/></svg>'

portfolio_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><rect width="400" height="200" fill="#F8FAFC"/><rect x="15" y="12" width="85" height="35" rx="3" fill="#E2E8F0"/><rect x="110" y="12" width="85" height="35" rx="3" fill="#E2E8F0"/><rect x="205" y="12" width="85" height="35" rx="3" fill="#E2E8F0"/><rect x="300" y="12" width="85" height="35" rx="3" fill="#E2E8F0"/><path d="M20,80 L380,80 L380,170 L20,170 Z" fill="#EFF6FF" stroke="#E2E8F0" stroke-width="1"/><rect x="60" y="95" width="45" height="55" rx="2" fill="#3B82F6" opacity="0.3"/><rect x="140" y="105" width="30" height="45" rx="2" fill="#3B82F6" opacity="0.5"/><rect x="200" y="110" width="25" height="40" rx="2" fill="#3B82F6" opacity="0.2"/><rect x="270" y="100" width="35" height="50" rx="2" fill="#3B82F6" opacity="0.4"/><rect x="330" y="120" width="20" height="30" rx="2" fill="#3B82F6" opacity="0.15"/><circle cx="80" cy="115" r="4" fill="#1E3A8A" opacity="0.5"/><circle cx="155" cy="120" r="3" fill="#1E3A8A" opacity="0.5"/><circle cx="290" cy="118" r="3.5" fill="#1E3A8A" opacity="0.5"/></svg>'

market_b64 = base64.b64encode(market_svg.encode()).decode()
portfolio_b64 = base64.b64encode(portfolio_svg.encode()).decode()

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

    .stApp { background-color: #F8FAFC; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1300px; }

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
    .home-logo-wrap img { height: 36px; display: block; }
    .home-subtitle {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.95rem; color: #64748B;
    }

    .nav-grid {
        display: flex; gap: 1.5rem; justify-content: center;
        margin-top: 2.5rem; flex-wrap: wrap;
    }

    .nav-card {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;
        width: 400px; overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
        text-decoration: none !important; display: block;
    }
    .nav-card:hover {
        border-color: #2563EB; box-shadow: 0 4px 12px rgba(37,99,235,0.12);
        transform: translateY(-2px);
    }

    .nav-card-preview {
        width: 100%; height: 140px; overflow: hidden;
        border-bottom: 1px solid #E2E8F0;
        display: flex; align-items: center; justify-content: center;
        background: #F8FAFC;
    }
    .nav-card-preview img {
        width: 100%; height: 100%; object-fit: cover;
        opacity: 0.7;
    }

    .nav-card-body {
        padding: 1.2rem 1.5rem;
        text-align: center;
    }

    .nav-card-title {
        font-family: 'DM Sans', sans-serif;
        font-size: 1.1rem; font-weight: 700; color: #1E293B;
        margin-bottom: 0.4rem; text-decoration: none !important;
    }
    .nav-card-desc {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.78rem; color: #64748B; line-height: 1.5;
        text-decoration: none !important;
    }

    a.nav-card, a.nav-card:hover, a.nav-card:visited, a.nav-card:active,
    a.nav-card *, a.nav-card:hover * { text-decoration: none !important; }

    .home-footer {
        text-align: center; font-family: 'DM Sans', sans-serif;
        font-size: 0.7rem; color: #94A3B8; margin-top: 4rem;
        padding-top: 1.5rem; border-top: 1px solid #E2E8F0;
    }

    @media (max-width: 768px) {
        .block-container { padding-top: 1rem; padding-left: 1rem; padding-right: 1rem; }
        .home-header { padding: 1rem 0 0.5rem 0; }
        .home-logo-wrap img { height: 28px; }
        .home-subtitle { font-size: 0.82rem; }
        .nav-grid { flex-direction: column; align-items: center; gap: 1rem; margin-top: 1.5rem; }
        .nav-card { width: 100%; max-width: 400px; }
        .nav-card-preview { height: 100px; }
        .nav-card-body { padding: 1rem 1.2rem; }
        .nav-card-title { font-size: 1rem; }
        .nav-card-desc { font-size: 0.72rem; }
        .home-footer { margin-top: 2rem; font-size: 0.65rem; }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

logo_img = ""
if logo_b64:
    logo_img = f'<div class="home-logo-wrap"><img src="data:{logo_mime};base64,{logo_b64}" /></div>'

watchlist_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><rect width="400" height="200" fill="#F8FAFC"/><rect x="15" y="12" width="370" height="6" rx="2" fill="#CBD5E1"/><rect x="15" y="28" width="120" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="28" width="40" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="260" y="28" width="35" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="320" y="28" width="40" height="4" rx="1" fill="#DC2626" opacity="0.4"/><rect x="15" y="40" width="100" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="40" width="30" height="4" rx="1" fill="#DC2626" opacity="0.5"/><rect x="260" y="40" width="45" height="4" rx="1" fill="#DC2626" opacity="0.4"/><rect x="320" y="40" width="35" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="15" y="52" width="110" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="52" width="35" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="260" y="52" width="30" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="320" y="52" width="45" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="15" y="72" width="370" height="6" rx="2" fill="#CBD5E1"/><rect x="15" y="88" width="90" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="88" width="35" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="260" y="88" width="40" height="4" rx="1" fill="#DC2626" opacity="0.4"/><rect x="320" y="88" width="30" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="15" y="100" width="105" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="100" width="40" height="4" rx="1" fill="#DC2626" opacity="0.5"/><rect x="260" y="100" width="35" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="320" y="100" width="40" height="4" rx="1" fill="#DC2626" opacity="0.4"/><rect x="15" y="120" width="370" height="6" rx="2" fill="#CBD5E1"/><rect x="15" y="136" width="80" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="136" width="35" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="15" y="148" width="95" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="148" width="40" height="4" rx="1" fill="#DC2626" opacity="0.5"/><rect x="15" y="160" width="85" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="160" width="30" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="15" y="172" width="110" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="172" width="45" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="15" y="184" width="75" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="184" width="35" height="4" rx="1" fill="#DC2626" opacity="0.5"/></svg>'
watchlist_b64 = base64.b64encode(watchlist_svg.encode()).decode()

st.markdown(f"""<div class="home-header">{logo_img}<div class="home-subtitle">Investment Intelligence Platform</div></div>""", unsafe_allow_html=True)

st.markdown(f"""<div class="nav-grid"><a class="nav-card" href="/Market_Dashboard" target="_self"><div class="nav-card-preview"><img src="data:image/svg+xml;base64,{market_b64}" /></div><div class="nav-card-body"><div class="nav-card-title">Market Dashboard</div><div class="nav-card-desc">Daily macro and market snapshot. Rates, equities, commodities, credit spreads, currencies, and volatility.</div></div></a><a class="nav-card" href="/Stock_Watchlist" target="_self"><div class="nav-card-preview"><img src="data:image/svg+xml;base64,{watchlist_b64}" /></div><div class="nav-card-body"><div class="nav-card-title">Stock Watchlist</div><div class="nav-card-desc">Live prices for core, connected, and global holdings. Track performance across exchanges and currencies.</div></div></a><a class="nav-card" href="/Portfolio_Dashboard" target="_self"><div class="nav-card-preview"><img src="data:image/svg+xml;base64,{portfolio_b64}" /></div><div class="nav-card-body"><div class="nav-card-title">Portfolio Dashboard</div><div class="nav-card-desc">Current investment allocations by geography, asset class, sector, and stage. Identify gaps and inform strategy.</div></div></a></div>""", unsafe_allow_html=True)

st.markdown("""<div class="home-footer">Secco Capital \u00b7 Investment Intelligence Platform \u00b7 Confidential</div>""", unsafe_allow_html=True)