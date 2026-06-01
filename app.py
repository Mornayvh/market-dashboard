"""
app.py — Secco Capital Platform Home Page
"""

import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

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

    .stApp {
        background:
            radial-gradient(1100px 460px at 50% -140px, rgba(79,127,214,0.10), rgba(79,127,214,0) 72%),
            linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 52%, #F1F5F9 100%);
        background-attachment: fixed;
    }
    .block-container { padding-top: 2.25rem; padding-bottom: 1.5rem; max-width: 1060px; }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    header[data-testid="stHeader"] { background: transparent; }

    /* ---- Hero ---- */
    .hero {
        display: flex; flex-direction: column; align-items: center;
        text-align: center; width: 100%; padding: 1.25rem 0 0.25rem 0;
    }
    .hero-eyebrow {
        display: flex; align-items: center; gap: 0.7rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; font-weight: 600;
        letter-spacing: 0.24em; text-transform: uppercase; color: #94A3B8;
        margin-bottom: 1.15rem;
    }
    .hero-eyebrow::before, .hero-eyebrow::after {
        content: ""; width: 26px; height: 1px; background: #CBD5E1;
    }
    .hero-logo { height: 128px; display: block; margin-bottom: 1.05rem; }
    .hero-title {
        font-family: 'DM Sans', sans-serif; font-size: 2.35rem; font-weight: 700;
        letter-spacing: -0.03em; color: #1E293B; line-height: 1.1; margin: 0;
    }
    .hero-sub {
        font-family: 'DM Sans', sans-serif; font-size: 1.02rem; color: #64748B;
        max-width: 530px; margin: 0.95rem auto 0; line-height: 1.6;
    }

    /* ---- Section kicker above carousel ---- */
    .section-kicker {
        display: flex; align-items: center; justify-content: center; gap: 0.8rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.64rem; font-weight: 600;
        letter-spacing: 0.22em; text-transform: uppercase; color: #94A3B8;
        margin: 2.6rem 0 0.2rem 0;
    }
    .section-kicker::before, .section-kicker::after {
        content: ""; height: 1px; width: 56px; background: #E2E8F0;
    }

    .carousel-hint {
        text-align: center; font-family: 'DM Sans', sans-serif;
        font-size: 0.76rem; color: #94A3B8; margin-top: 0.1rem;
    }

    /* ---- Footer ---- */
    .home-footer {
        display: flex; justify-content: space-between; align-items: center; gap: 1rem;
        max-width: 1060px; margin: 2.75rem auto 0 auto; padding-top: 1.4rem;
        border-top: 1px solid #E2E8F0;
        font-family: 'DM Sans', sans-serif; font-size: 0.72rem; color: #94A3B8;
    }
    .home-footer .brand {
        font-weight: 700; color: #475569; letter-spacing: 0.06em; text-transform: uppercase;
        font-size: 0.7rem;
    }
    .home-footer .meta { display: flex; gap: 1.3rem; }

    @media (max-width: 768px) {
        .block-container { padding-top: 1rem; padding-left: 1rem; padding-right: 1rem; }
        .hero { padding-top: 0.5rem; }
        .hero-logo { height: 88px; }
        .hero-title { font-size: 1.7rem; }
        .hero-sub { font-size: 0.9rem; }
        .section-kicker { margin-top: 1.8rem; }
        .section-kicker::before, .section-kicker::after { width: 28px; }
        .home-footer { flex-direction: column; gap: 0.5rem; text-align: center; margin-top: 2rem; }
        .home-footer .meta { gap: 0.9rem; }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

logo_img = ""
if logo_b64:
    logo_img = f'<img class="hero-logo" src="data:{logo_mime};base64,{logo_b64}" />'

watchlist_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><rect width="400" height="200" fill="#F8FAFC"/><rect x="15" y="12" width="370" height="6" rx="2" fill="#CBD5E1"/><rect x="15" y="28" width="120" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="28" width="40" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="260" y="28" width="35" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="320" y="28" width="40" height="4" rx="1" fill="#DC2626" opacity="0.4"/><rect x="15" y="40" width="100" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="40" width="30" height="4" rx="1" fill="#DC2626" opacity="0.5"/><rect x="260" y="40" width="45" height="4" rx="1" fill="#DC2626" opacity="0.4"/><rect x="320" y="40" width="35" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="15" y="52" width="110" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="52" width="35" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="260" y="52" width="30" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="320" y="52" width="45" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="15" y="72" width="370" height="6" rx="2" fill="#CBD5E1"/><rect x="15" y="88" width="90" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="88" width="35" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="260" y="88" width="40" height="4" rx="1" fill="#DC2626" opacity="0.4"/><rect x="320" y="88" width="30" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="15" y="100" width="105" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="100" width="40" height="4" rx="1" fill="#DC2626" opacity="0.5"/><rect x="260" y="100" width="35" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="320" y="100" width="40" height="4" rx="1" fill="#DC2626" opacity="0.4"/><rect x="15" y="120" width="370" height="6" rx="2" fill="#CBD5E1"/><rect x="15" y="136" width="80" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="136" width="35" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="15" y="148" width="95" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="148" width="40" height="4" rx="1" fill="#DC2626" opacity="0.5"/><rect x="15" y="160" width="85" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="160" width="30" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="15" y="172" width="110" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="172" width="45" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="15" y="184" width="75" height="4" rx="1" fill="#E2E8F0"/><rect x="200" y="184" width="35" height="4" rx="1" fill="#DC2626" opacity="0.5"/></svg>'
watchlist_b64 = base64.b64encode(watchlist_svg.encode()).decode()

direct_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><rect width="400" height="200" fill="#F8FAFC"/><rect x="15" y="15" width="160" height="55" rx="4" fill="#FFFFFF" stroke="#E2E8F0"/><rect x="25" y="25" width="60" height="4" rx="1" fill="#1E293B"/><rect x="25" y="35" width="100" height="3" rx="1" fill="#E2E8F0"/><rect x="25" y="44" width="80" height="3" rx="1" fill="#16A34A" opacity="0.5"/><rect x="25" y="53" width="65" height="3" rx="1" fill="#DC2626" opacity="0.4"/><rect x="225" y="15" width="160" height="55" rx="4" fill="#FFFFFF" stroke="#4F7FD6" stroke-width="1.5"/><rect x="235" y="25" width="70" height="4" rx="1" fill="#1E293B"/><rect x="235" y="35" width="90" height="3" rx="1" fill="#E2E8F0"/><rect x="235" y="44" width="100" height="3" rx="1" fill="#16A34A" opacity="0.6"/><rect x="235" y="53" width="55" height="3" rx="1" fill="#16A34A" opacity="0.4"/><polyline points="20,170 60,160 100,155 140,140 180,148 220,128 260,118 300,112 340,98 380,90" fill="none" stroke="#4F7FD6" stroke-width="2"/><polyline points="20,175 60,170 100,166 140,160 180,162 220,152 260,148 300,142 340,135 380,130" fill="none" stroke="#94A3B8" stroke-width="1" opacity="0.5"/><polyline points="20,178 60,174 100,172 140,168 180,170 220,164 260,160 300,158 340,154 380,150" fill="none" stroke="#94A3B8" stroke-width="1" opacity="0.5"/></svg>'
direct_b64 = base64.b64encode(direct_svg.encode()).decode()

altmgr_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><rect width="400" height="200" fill="#F8FAFC"/><rect x="15" y="14" width="370" height="5" rx="2" fill="#CBD5E1"/><rect x="15" y="28" width="70" height="4" rx="1" fill="#E2E8F0"/><rect x="120" y="28" width="40" height="4" rx="1" fill="#4F7FD6" opacity="0.6"/><rect x="190" y="28" width="35" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="260" y="28" width="40" height="4" rx="1" fill="#DC2626" opacity="0.4"/><rect x="320" y="28" width="50" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="15" y="40" width="70" height="4" rx="1" fill="#E2E8F0"/><rect x="120" y="40" width="40" height="4" rx="1" fill="#4F7FD6" opacity="0.6"/><rect x="190" y="40" width="35" height="4" rx="1" fill="#DC2626" opacity="0.5"/><rect x="260" y="40" width="40" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="320" y="40" width="50" height="4" rx="1" fill="#16A34A" opacity="0.4"/><rect x="15" y="52" width="70" height="4" rx="1" fill="#E2E8F0"/><rect x="120" y="52" width="40" height="4" rx="1" fill="#4F7FD6" opacity="0.6"/><rect x="190" y="52" width="35" height="4" rx="1" fill="#16A34A" opacity="0.5"/><rect x="260" y="52" width="40" height="4" rx="1" fill="#DC2626" opacity="0.4"/><rect x="320" y="52" width="50" height="4" rx="1" fill="#DC2626" opacity="0.4"/><polyline points="20,180 60,165 100,168 140,150 180,155 220,135 260,138 300,120 340,110 380,100" fill="none" stroke="#4F7FD6" stroke-width="2"/><polyline points="20,185 60,178 100,180 140,170 180,172 220,162 260,165 300,158 340,150 380,145" fill="none" stroke="#16A34A" stroke-width="1.4" opacity="0.6"/><polyline points="20,188 60,184 100,182 140,180 180,178 220,176 260,172 300,170 340,168 380,164" fill="none" stroke="#94A3B8" stroke-width="1" opacity="0.5"/></svg>'
altmgr_b64 = base64.b64encode(altmgr_svg.encode()).decode()

st.markdown(
    f"""<div class="hero">
        <div class="hero-eyebrow">Internal Platform</div>
        {logo_img}
        <h1 class="hero-title">Investment Intelligence Platform</h1>
        <p class="hero-sub">Markets, portfolio, holdings, and alternative managers &mdash; a single live view, updated in real time.</p>
    </div>""",
    unsafe_allow_html=True,
)

# Card registry — each slide links to a page
CARDS = [
    ("/Market_Dashboard", market_b64, "Market Dashboard",
     "Daily macro and market snapshot. Rates, equities, commodities, credit spreads, currencies, and volatility."),
    ("/Portfolio_Dashboard", portfolio_b64, "Portfolio Dashboard",
     "Current investment allocations by geography, asset class, sector, and stage. Identify gaps and inform strategy."),
    ("/Stock_Watchlist", watchlist_b64, "Stock Watchlist",
     "Live prices for core, connected, and global holdings. Track performance across exchanges and currencies."),
    ("/Direct_Investments", direct_b64, "Direct Investments",
     "Public-market proxy tracker for private holdings. Comps, sector ETFs, capex, sentiment for Novolex, Kelvion, Real Chemistry."),
    ("/Alt_Managers", altmgr_b64, "Alternative Managers",
     "Compare 19 listed alternative asset managers as stocks. Valuation, returns, and risk across Blackstone, KKR, Apollo, Brookfield and peers."),
]

# Build the slides + dots; the carousel is rendered inside a sandboxed
# components.html iframe so its JavaScript controls actually fire (Streamlit's
# markdown sanitiser strips ids/anchors, which broke the pure-CSS version).
slides = ""
for href, img_b64, title, desc in CARDS:
    slides += (
        f'<div class="slide">'
        f'<div class="nav-card" data-href="{href}">'
        f'<div class="nav-card-preview"><img src="data:image/svg+xml;base64,{img_b64}" /></div>'
        f'<div class="nav-card-body"><div class="nav-card-title">{title}</div>'
        f'<div class="nav-card-desc">{desc}</div></div></div>'
        f'</div>'
    )

dots = "".join('<button class="dot"></button>' for _ in CARDS)

carousel_html = f"""
<!doctype html><html><head><meta charset="utf-8">
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}

    .carousel {{ position: relative; width: 100%; height: 380px; overflow: hidden; }}
    .track {{
        position: absolute; top: 30px; left: 50%;
        display: flex; align-items: flex-start; gap: 28px;
        transition: transform 0.45s cubic-bezier(0.22, 0.61, 0.36, 1);
    }}
    .slide {{ flex: 0 0 300px; width: 300px; display: flex; justify-content: center; }}

    .nav-card {{
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;
        width: 300px; height: 300px; overflow: hidden; cursor: pointer;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        filter: blur(3px) saturate(0.85); opacity: 0.45; transform: scale(0.8);
        transition: transform 0.45s ease, filter 0.45s ease, opacity 0.45s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }}
    .nav-card.active {{
        filter: none; opacity: 1; transform: scale(1);
        box-shadow: 0 12px 32px rgba(15,23,42,0.14); position: relative; z-index: 3;
    }}
    .nav-card.active:hover {{ border-color: #4F7FD6; box-shadow: 0 14px 36px rgba(79,127,214,0.2); }}

    .nav-card-preview {{
        width: 100%; height: 120px; overflow: hidden;
        border-bottom: 1px solid #E2E8F0;
        display: flex; align-items: center; justify-content: center; background: #F8FAFC;
    }}
    .nav-card-preview img {{ width: 100%; height: 100%; object-fit: cover; opacity: 0.7; }}
    .nav-card-body {{ padding: 1.2rem 1.5rem; text-align: center; }}
    .nav-card-title {{
        font-family: 'DM Sans', sans-serif; font-size: 1.1rem; font-weight: 700;
        color: #1E293B; margin-bottom: 0.4rem;
    }}
    .nav-card-desc {{
        font-family: 'DM Sans', sans-serif; font-size: 0.78rem; color: #64748B; line-height: 1.5;
    }}

    .arrow {{
        position: absolute; top: 180px; transform: translateY(-50%);
        width: 42px; height: 42px; border-radius: 50%;
        background: #FFFFFF; border: 1px solid #E2E8F0; cursor: pointer;
        display: flex; align-items: center; justify-content: center;
        color: #475569; font-family: 'DM Sans', sans-serif; font-size: 1.5rem; line-height: 1;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12); transition: all 0.2s ease; z-index: 7;
    }}
    .arrow:hover {{ border-color: #4F7FD6; color: #4F7FD6; box-shadow: 0 4px 14px rgba(79,127,214,0.22); }}
    .arrow.left {{ left: calc(50% - 200px); }}
    .arrow.right {{ left: calc(50% + 158px); }}

    .dots {{
        position: absolute; bottom: 14px; left: 0; right: 0;
        display: flex; gap: 0.5rem; justify-content: center; z-index: 7;
    }}
    .dot {{
        width: 8px; height: 8px; border-radius: 50%; border: none; padding: 0;
        background: #CBD5E1; cursor: pointer; transition: all 0.2s ease;
    }}
    .dot:hover {{ background: #94A3B8; }}
    .dot.active {{ background: #4F7FD6; width: 22px; border-radius: 4px; }}

    @media (max-width: 768px) {{
        .arrow {{ top: 175px; width: 36px; height: 36px; font-size: 1.3rem; }}
        .arrow.left {{ left: calc(50% - 174px); }}
        .arrow.right {{ left: calc(50% + 138px); }}
    }}
</style></head>
<body>
<div class="carousel">
    <div class="track">{slides}</div>
    <button class="arrow left" aria-label="Previous">&lsaquo;</button>
    <button class="arrow right" aria-label="Next">&rsaquo;</button>
    <div class="dots">{dots}</div>
</div>
<script>
    const STEP = 328, CARD_CENTER = 150;
    const cards = Array.from(document.querySelectorAll('.nav-card'));
    const dots  = Array.from(document.querySelectorAll('.dot'));
    const track = document.querySelector('.track');
    const n = cards.length;
    let cur = 0;

    function render() {{
        track.style.transform = 'translateX(' + (-(CARD_CENTER + cur * STEP)) + 'px)';
        cards.forEach((c, i) => c.classList.toggle('active', i === cur));
        dots.forEach((d, i) => d.classList.toggle('active', i === cur));
    }}
    document.querySelector('.arrow.left').addEventListener('click', () => {{ cur = (cur - 1 + n) % n; render(); }});
    document.querySelector('.arrow.right').addEventListener('click', () => {{ cur = (cur + 1) % n; render(); }});
    dots.forEach((d, i) => d.addEventListener('click', () => {{ cur = i; render(); }}));
    cards.forEach((c, i) => c.addEventListener('click', () => {{
        if (i !== cur) {{ cur = i; render(); return; }}        // clicking a side card centres it first
        window.top.location.pathname = c.dataset.href;          // clicking the centred card opens the page
    }}));
    render();
</script>
</body></html>
"""

st.markdown(
    f'<div class="section-kicker">Explore the dashboards \u00b7 {len(CARDS)} workspaces</div>',
    unsafe_allow_html=True,
)

components.html(carousel_html, height=400)

st.markdown(
    '<div class="carousel-hint">Use the arrows or dots to browse \u00b7 click the centre card to open it</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """<div class="home-footer">
        <span class="brand">Secco Capital</span>
        <span class="meta"><span>Investment Intelligence Platform</span><span>Confidential</span><span>&copy; 2026</span></span>
    </div>""",
    unsafe_allow_html=True,
)
