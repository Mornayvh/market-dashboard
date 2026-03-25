"""
app.py — Secco Capital Platform Home Page
Landing page with navigation to all dashboards.
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
# CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

    .stApp { background-color: #F8FAFC; }

    .block-container {
        padding-top: 3rem;
        padding-bottom: 2rem;
        max-width: 900px;
    }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    header[data-testid="stHeader"] { background: #F8FAFC; }

    .home-header { text-align: center; padding: 2rem 0 1rem 0; }
    .home-logo { height: 48px; margin-bottom: 1rem; }
    .home-title {
        font-family: 'DM Sans', sans-serif;
        font-size: 2rem; font-weight: 700; color: #1E293B;
        letter-spacing: -0.02em; margin-bottom: 0.3rem;
    }
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
        padding: 2rem; width: 340px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: all 0.2s ease; text-decoration: none; display: block;
    }
    .nav-card:hover {
        border-color: #2563EB; box-shadow: 0 4px 12px rgba(37,99,235,0.1);
        transform: translateY(-2px);
    }
    .nav-card-icon { font-size: 1.8rem; margin-bottom: 0.8rem; }
    .nav-card-title {
        font-family: 'DM Sans', sans-serif;
        font-size: 1.1rem; font-weight: 700; color: #1E293B; margin-bottom: 0.4rem;
    }
    .nav-card-desc {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.82rem; color: #64748B; line-height: 1.5;
    }
    .nav-card-status {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem; color: #94A3B8; margin-top: 1rem;
        text-transform: uppercase; letter-spacing: 0.08em;
    }
    .status-live { color: #16A34A; }

    .home-footer {
        text-align: center; font-family: 'DM Sans', sans-serif;
        font-size: 0.7rem; color: #94A3B8; margin-top: 4rem;
        padding-top: 1.5rem; border-top: 1px solid #E2E8F0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Logo
# ---------------------------------------------------------------------------

logo_html = ""
for ext in ["png", "svg", "jpg"]:
    logo_path = Path(__file__).parent / f"logo.{ext}"
    if logo_path.exists():
        if ext == "svg":
            logo_html = f'<div class="home-logo">{logo_path.read_text()}</div>'
        else:
            b64 = base64.b64encode(logo_path.read_bytes()).decode()
            logo_html = f'<img class="home-logo" src="data:image/{ext};base64,{b64}" />'
        break

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

st.markdown(f"""<div class="home-header">{logo_html}<div class="home-title">Secco Capital</div><div class="home-subtitle">Investment Intelligence Platform</div></div>""", unsafe_allow_html=True)

st.markdown("""<div class="nav-grid"><a class="nav-card" href="/Market_Dashboard" target="_self"><div class="nav-card-icon">📊</div><div class="nav-card-title">Market Dashboard</div><div class="nav-card-desc">Daily macro and market snapshot. Rates, equities, commodities, credit spreads, currencies, and volatility.</div><div class="nav-card-status status-live">● Live</div></a><a class="nav-card" href="/Portfolio_Dashboard" target="_self"><div class="nav-card-icon">🗺️</div><div class="nav-card-title">Portfolio Dashboard</div><div class="nav-card-desc">Current investment allocations by geography, asset class, sector, and stage. Identify gaps and inform strategy.</div><div class="nav-card-status status-live">● Live</div></a></div>""", unsafe_allow_html=True)

st.markdown("""<div class="home-footer">Secco Capital · Investment Intelligence Platform · Confidential</div>""", unsafe_allow_html=True)
