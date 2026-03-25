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
logo_path = Path(__file__).parent / "logo.svg"
if not logo_path.exists():
    # Try alternate names
    for name in ["Secco_logo.svg", "logo.png", "Secco_logo.png"]:
        alt = Path(__file__).parent / name
        if alt.exists():
            logo_path = alt
            break

if logo_path.exists():
    if logo_path.suffix == ".svg":
        svg_content = logo_path.read_text()
        logo_html = f'<div style="display:flex; justify-content:center; margin-bottom:0.8rem;"><div style="height:32px; overflow:hidden;">{svg_content}</div></div>'
    else:
        b64 = base64.b64encode(logo_path.read_bytes()).decode()
        logo_html = f'<div style="display:flex; justify-content:center; margin-bottom:0.8rem;"><img style="height:32px;" src="data:image/{logo_path.suffix[1:]};base64,{b64}" /></div>'
else:
    logo_html = ""

# ---------------------------------------------------------------------------
# Generate preview screenshots as simple SVG placeholders
# ---------------------------------------------------------------------------

market_preview_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">
<rect width="400" height="200" fill="#F1F5F9"/>
<rect x="20" y="15" width="55" height="30" rx="3" fill="#E2E8F0"/>
<rect x="85" y="15" width="55" height="30" rx="3" fill="#E2E8F0"/>
<rect x="150" y="15" width="55" height="30" rx="3" fill="#E2E8F0"/>
<rect x="215" y="15" width="55" height="30" rx="3" fill="#E2E8F0"/>
<rect x="280" y="15" width="55" height="30" rx="3" fill="#E2E8F0"/>
<rect x="345" y="15" width="40" height="30" rx="3" fill="#E2E8F0"/>
<rect x="20" y="60" width="170" height="8" rx="2" fill="#CBD5E1"/>
<rect x="20" y="75" width="170" height="5" rx="1" fill="#E2E8F0"/>
<rect x="20" y="85" width="170" height="5" rx="1" fill="#E2E8F0"/>
<rect x="20" y="95" width="170" height="5" rx="1" fill="#E2E8F0"/>
<rect x="210" y="60" width="170" height="8" rx="2" fill="#CBD5E1"/>
<rect x="210" y="75" width="170" height="5" rx="1" fill="#E2E8F0"/>
<rect x="210" y="85" width="170" height="5" rx="1" fill="#E2E8F0"/>
<rect x="210" y="95" width="170" height="5" rx="1" fill="#E2E8F0"/>
<polyline points="20,170 60,155 100,160 140,145 180,150 220,135 260,140 300,130 340,138 380,125" fill="none" stroke="#16A34A" stroke-width="2"/>
<polyline points="20,175 60,168 100,172 140,160 180,165 220,155 260,158 300,148 340,152 380,145" fill="none" stroke="#DC2626" stroke-width="2"/>
</svg>"""

portfolio_preview_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">
<rect width="400" height="200" fill="#F1F5F9"/>
<rect x="20" y="15" width="80" height="40" rx="3" fill="#E2E8F0"/>
<rect x="110" y="15" width="80" height="40" rx="3" fill="#E2E8F0"/>
<rect x="200" y="15" width="80" height="40" rx="3" fill="#E2E8F0"/>
<rect x="290" y="15" width="90" height="40" rx="3" fill="#E2E8F0"/>
<rect x="20" y="70" width="8" height="12" rx="1" fill="#2563EB"/>
<rect x="20" y="88" width="8" height="10" rx="1" fill="#2563EB"/>
<rect x="20" y="104" width="8" height="8" rx="1" fill="#2563EB"/>
<rect x="32" y="72" width="80" height="6" rx="1" fill="#2563EB" opacity="0.7"/>
<rect x="32" y="90" width="60" height="6" rx="1" fill="#2563EB" opacity="0.6"/>
<rect x="32" y="106" width="45" height="6" rx="1" fill="#2563EB" opacity="0.5"/>
<ellipse cx="280" cy="140" rx="80" ry="45" fill="none" stroke="#CBD5E1" stroke-width="1"/>
<path d="M240,100 Q260,90 300,95 Q340,100 350,120 Q355,140 340,155 Q320,170 280,170 Q250,170 235,155 Q220,140 225,120 Q230,105 240,100Z" fill="#2563EB" opacity="0.15" stroke="#2563EB" stroke-width="1" opacity="0.3"/>
<circle cx="300" cy="120" r="3" fill="#2563EB"/>
<circle cx="260" cy="135" r="3" fill="#7C3AED"/>
<circle cx="320" cy="145" r="3" fill="#059669"/>
</svg>"""

market_b64 = base64.b64encode(market_preview_svg.encode()).decode()
portfolio_b64 = base64.b64encode(portfolio_preview_svg.encode()).decode()

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

    .stApp {{ background-color: #F8FAFC; }}
    .block-container {{ padding-top: 3rem; padding-bottom: 2rem; max-width: 1000px; }}

    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    .stDeployButton {{ display: none; }}
    header[data-testid="stHeader"] {{ background: #F8FAFC; }}

    .home-header {{ text-align: center; padding: 2rem 0 1rem 0; }}
    .home-title {{
        font-family: 'DM Sans', sans-serif;
        font-size: 2rem; font-weight: 700; color: #1E293B;
        letter-spacing: -0.02em; margin-bottom: 0.3rem;
    }}
    .home-subtitle {{
        font-family: 'DM Sans', sans-serif;
        font-size: 0.95rem; color: #64748B;
    }}

    .nav-grid {{
        display: flex; gap: 1.5rem; justify-content: center;
        margin-top: 2.5rem; flex-wrap: wrap;
    }}

    .nav-card {{
        position: relative; overflow: hidden;
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;
        width: 380px; height: 260px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
        text-decoration: none !important; display: block;
    }}
    .nav-card:hover {{
        border-color: #2563EB; box-shadow: 0 4px 12px rgba(37,99,235,0.12);
        transform: translateY(-2px);
    }}

    .nav-card-bg {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-size: cover; background-position: center;
        opacity: 0.25;
    }}

    .nav-card-overlay {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: linear-gradient(180deg, rgba(255,255,255,0.6) 0%, rgba(255,255,255,0.95) 60%);
    }}

    .nav-card-content {{
        position: relative; z-index: 1;
        display: flex; flex-direction: column;
        justify-content: center; align-items: center;
        height: 100%; padding: 1.5rem 2rem;
        text-align: center;
    }}

    .nav-card-title {{
        font-family: 'DM Sans', sans-serif;
        font-size: 1.2rem; font-weight: 700; color: #1E293B;
        margin-bottom: 0.6rem;
        text-decoration: none !important;
    }}
    .nav-card-desc {{
        font-family: 'DM Sans', sans-serif;
        font-size: 0.8rem; color: #64748B; line-height: 1.5;
        text-decoration: none !important;
        max-width: 280px;
    }}

    a.nav-card, a.nav-card:hover, a.nav-card:visited, a.nav-card:active {{
        text-decoration: none !important;
    }}

    .home-footer {{
        text-align: center; font-family: 'DM Sans', sans-serif;
        font-size: 0.7rem; color: #94A3B8; margin-top: 4rem;
        padding-top: 1.5rem; border-top: 1px solid #E2E8F0;
    }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

st.markdown(f"""<div class="home-header">{logo_html}<div class="home-subtitle">Investment Intelligence Platform</div></div>""", unsafe_allow_html=True)

st.markdown(f"""<div class="nav-grid"><a class="nav-card" href="/Market_Dashboard" target="_self"><div class="nav-card-bg" style="background-image:url('data:image/svg+xml;base64,{market_b64}');"></div><div class="nav-card-overlay"></div><div class="nav-card-content"><div class="nav-card-title">Market Dashboard</div><div class="nav-card-desc">Daily macro and market snapshot. Rates, equities, commodities, credit spreads, currencies, and volatility.</div></div></a><a class="nav-card" href="/Portfolio_Dashboard" target="_self"><div class="nav-card-bg" style="background-image:url('data:image/svg+xml;base64,{portfolio_b64}');"></div><div class="nav-card-overlay"></div><div class="nav-card-content"><div class="nav-card-title">Portfolio Dashboard</div><div class="nav-card-desc">Current investment allocations by geography, asset class, sector, and stage. Identify gaps and inform strategy.</div></div></a></div>""", unsafe_allow_html=True)

st.markdown("""<div class="home-footer">Secco Capital · Investment Intelligence Platform · Confidential</div>""", unsafe_allow_html=True)
