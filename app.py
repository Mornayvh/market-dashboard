"""
app.py — Secco Capital Platform Home Page

Renders the entire front page (topbar + live clock, ticker strip, hero, and the
dashboard carousel) inside ONE sandboxed components.html iframe. This is required
because Streamlit's st.markdown sanitiser strips <script> tags, so the live clock,
ticker updates, and carousel controls can only run from inside a component iframe.

Drop this file in at market-dashboard/app.py (replacing the existing one).
It reads logo.png from the same folder, exactly like the current version.
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
# Load logo -> base64 data URI (must be inlined; the iframe can't read local files)
# ---------------------------------------------------------------------------
root = Path(__file__).parent
logo_uri = ""
for name, mime in [("logo.png", "image/png"), ("logo.svg", "image/svg+xml")]:
    p = root / name
    if p.exists():
        logo_uri = f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
        break

# ---------------------------------------------------------------------------
# Dashboard cards — (streamlit page path, title, description, tag, preview SVG)
# The page paths must match the filenames in pages/ (Streamlit slugifies them).
# ---------------------------------------------------------------------------
ACCENT = "#4F7FD6"

CARDS = [
    (
        "/Market_Dashboard", "Market Dashboard", "Macro · Daily",
        "Daily macro snapshot — rates, equities, commodities, credit spreads, FX and volatility in a single glance.",
        '''<svg viewBox="0 0 300 132" width="100%" height="100%" preserveAspectRatio="none">
             <line x1="0" y1="40" x2="300" y2="40" stroke="#EDF1F5"/><line x1="0" y1="72" x2="300" y2="72" stroke="#EDF1F5"/><line x1="0" y1="104" x2="300" y2="104" stroke="#EDF1F5"/>
             <path d="M0,100 L37,92 L75,95 L112,80 L150,86 L187,66 L225,72 L262,52 L300,46 L300,132 L0,132 Z" fill="var(--accent)" opacity="0.09"/>
             <polyline points="0,100 37,92 75,95 112,80 150,86 187,66 225,72 262,52 300,46" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>
             <polyline points="0,112 37,108 75,110 112,102 150,105 187,98 225,100 262,92 300,90" fill="none" stroke="#94A3B8" stroke-width="1.4" opacity="0.55"/>
           </svg>''',
    ),
    (
        "/Partner_Dashboard", "Partner Dashboard", "Portfolio",
        "Allocations across geography, asset class, sector and stage. Spot the gaps, shape the strategy.",
        '''<svg viewBox="0 0 132 132" width="132" height="132" style="display:block;margin:0 auto;">
             <g transform="rotate(-90 66 66)" fill="none" stroke-width="15">
               <circle cx="66" cy="66" r="38" stroke="var(--accent)" stroke-dasharray="96 143"/>
               <circle cx="66" cy="66" r="38" stroke="#64748B" stroke-dasharray="60 179" stroke-dashoffset="-96"/>
               <circle cx="66" cy="66" r="38" stroke="#A9B6C6" stroke-dasharray="48 191" stroke-dashoffset="-156"/>
               <circle cx="66" cy="66" r="38" stroke="#D3DBE4" stroke-dasharray="35 204" stroke-dashoffset="-204"/>
             </g>
             <text x="66" y="63" text-anchor="middle" style="font:700 15px 'JetBrains Mono',monospace;fill:#0F172A;">62%</text>
             <text x="66" y="78" text-anchor="middle" style="font:600 7.5px 'JetBrains Mono',monospace;fill:#94A3B8;letter-spacing:0.1em;">DEPLOYED</text>
           </svg>''',
    ),
    (
        "/Stock_Watchlist", "Stock Watchlist", "Live Prices",
        "Live prices for core, connected and global holdings across exchanges and currencies.",
        '''<div style="padding:16px 20px;display:flex;flex-direction:column;justify-content:center;gap:9px;height:100%;">
             <div class="wl-row"><span>NVDA</span><span style="color:#16A34A;">&#9650; 2.14%</span></div>
             <div class="wl-row"><span>MSFT</span><span style="color:#16A34A;">&#9650; 0.38%</span></div>
             <div class="wl-row"><span>ASML</span><span style="color:#DC2626;">&#9660; 1.02%</span></div>
             <div class="wl-row"><span>NPN.JO</span><span style="color:#16A34A;">&#9650; 0.71%</span></div>
           </div>''',
    ),
    (
        "/Direct_Investments", "Direct Investments", "Novolex · Kelvion · Real Chem",
        "Public-market proxy tracker for private holdings — comps, sector ETFs, capex and sentiment.",
        '''<svg viewBox="0 0 300 132" width="100%" height="100%" preserveAspectRatio="none">
             <polyline points="0,110 37,104 75,106 112,96 150,100 187,90 225,92 262,84 300,80" fill="none" stroke="#C3CDD9" stroke-width="1.4" opacity="0.7"/>
             <polyline points="0,118 37,116 75,112 112,110 150,106 187,104 225,98 262,96 300,90" fill="none" stroke="#C3CDD9" stroke-width="1.4" opacity="0.5"/>
             <path d="M0,104 L37,96 L75,88 L112,84 L150,68 L187,58 L225,50 L262,38 L300,30 L300,132 L0,132 Z" fill="var(--accent)" opacity="0.08"/>
             <polyline points="0,104 37,96 75,88 112,84 150,68 187,58 225,50 262,38 300,30" fill="none" stroke="var(--accent)" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>
             <circle cx="300" cy="30" r="3.4" fill="var(--accent)"/>
           </svg>''',
    ),
    (
        "/Alt_Managers", "Alternative Managers", "Blackstone · KKR · Apollo",
        "19 listed alternative managers compared as stocks — valuation, returns and risk, side by side.",
        '''<svg viewBox="0 0 300 132" width="100%" height="100%" preserveAspectRatio="none">
             <line x1="18" y1="112" x2="282" y2="112" stroke="#E2E8F0"/>
             <rect x="24" y="72" width="20" height="40" rx="2" fill="#D3DBE4"/><rect x="54" y="57" width="20" height="55" rx="2" fill="#C3CDD9"/>
             <rect x="84" y="64" width="20" height="48" rx="2" fill="#D3DBE4"/><rect x="114" y="42" width="20" height="70" rx="2" fill="#A9B6C6"/>
             <rect x="144" y="52" width="20" height="60" rx="2" fill="#C3CDD9"/><rect x="174" y="27" width="20" height="85" rx="2" fill="var(--accent)"/>
             <rect x="204" y="60" width="20" height="52" rx="2" fill="#C3CDD9"/><rect x="234" y="46" width="20" height="66" rx="2" fill="#D3DBE4"/>
           </svg>''',
    ),
]

cards_html = ""
for href, title, desc, tag, preview in CARDS:
    cards_html += f'''
      <div class="card" data-card data-href="{href}">
        <div class="card-preview">{preview}</div>
        <div class="card-body">
          <div class="card-title">{title}</div>
          <p class="card-desc">{desc}</p>
          <div class="card-foot"><span class="card-tag">{tag}</span><span class="card-open">Open &#8594;</span></div>
        </div>
      </div>'''

dots_html = "".join(
    f'<button data-dot class="dot{" active" if i == 0 else ""}" aria-label="Slide {i+1}"></button>'
    for i in range(len(CARDS))
)

logo_img = f'<img src="{logo_uri}" alt="Secco Capital" class="logo"/>' if logo_uri else ""

# ---------------------------------------------------------------------------
# Hide Streamlit chrome on the home page
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
      .block-container { padding: 0 !important; max-width: 100% !important; }
      #MainMenu, footer, .stDeployButton { visibility: hidden; }
      header[data-testid="stHeader"] { background: transparent; }
      .stApp { background: #FFFFFF; }
      iframe { border: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# The whole front page as one self-contained document (styles + script inline)
# ---------------------------------------------------------------------------
PAGE = r"""
<!doctype html><html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  *{box-sizing:border-box;} html,body{margin:0;padding:0;}
  :root{--accent:__ACCENT__;}
  body{font-family:'DM Sans',system-ui,sans-serif;color:#1E293B;
    background:radial-gradient(1200px 520px at 50% -180px, rgba(79,127,214,0.10), rgba(79,127,214,0) 70%), linear-gradient(180deg,#FFFFFF 0%,#F8FAFC 55%,#F1F5F9 100%);}
  @keyframes marquee{from{transform:translateX(0);}to{transform:translateX(-50%);}}
  @keyframes livepulse{0%{transform:scale(1);opacity:1;}70%{transform:scale(2.6);opacity:0;}100%{opacity:0;}}

  .bar{width:100%;border-bottom:1px solid #E9EDF2;background:rgba(255,255,255,0.72);backdrop-filter:blur(8px);}
  .bar-in{max-width:1180px;margin:0 auto;padding:16px 32px;display:flex;align-items:center;justify-content:space-between;gap:24px;}
  .brand{display:flex;align-items:center;gap:14px;}
  .logo{height:30px;width:auto;display:block;}
  .divider{width:1px;height:22px;background:#E2E8F0;}
  .platform{font:600 10px 'JetBrains Mono',monospace;letter-spacing:.22em;text-transform:uppercase;color:#94A3B8;}
  .clocks{display:flex;align-items:center;gap:20px;}
  .clock{text-align:right;}
  .clock .t{font:600 13px 'JetBrains Mono',monospace;color:#0F172A;letter-spacing:.02em;}
  .clock .c{font:600 9px 'JetBrains Mono',monospace;letter-spacing:.16em;text-transform:uppercase;color:#94A3B8;margin-top:2px;}
  .vd{width:1px;height:26px;background:#E2E8F0;}
  .live{display:flex;align-items:center;gap:7px;padding:6px 12px;border:1px solid #E2E8F0;border-radius:999px;background:#FFF;}
  .live .ring{position:relative;display:inline-flex;width:7px;height:7px;}
  .live .ring b{position:absolute;inset:0;border-radius:50%;background:#16A34A;animation:livepulse 2.2s ease-out infinite;}
  .live .ring i{position:relative;width:7px;height:7px;border-radius:50%;background:#16A34A;}
  .live span{font:700 10px 'JetBrains Mono',monospace;letter-spacing:.16em;color:#15803D;}

  .ticker{width:100%;border-bottom:1px solid #E9EDF2;background:linear-gradient(180deg,#FFF,#FBFCFE);overflow:hidden;}
  .ticker-track{display:inline-flex;align-items:center;height:46px;animation:marquee 48s linear infinite;will-change:transform;}
  .ticker:hover .ticker-track{animation-play-state:paused;}
  .tk{display:flex;align-items:baseline;gap:9px;padding:0 22px;border-right:1px solid #EDF1F5;white-space:nowrap;}
  .tk .s{font:600 11px 'JetBrains Mono',monospace;letter-spacing:.03em;color:#64748B;}
  .tk .v{font:600 12.5px 'JetBrains Mono',monospace;color:#0F172A;transition:background .4s ease;padding:1px 3px;border-radius:3px;}
  .tk .g{font:600 11px 'JetBrains Mono',monospace;}

  .hero{max-width:1100px;margin:0 auto;padding:72px 32px 34px;text-align:center;display:flex;flex-direction:column;align-items:center;}
  .eyebrow{display:flex;align-items:center;gap:12px;font:600 10.5px 'JetBrains Mono',monospace;letter-spacing:.26em;text-transform:uppercase;color:#94A3B8;margin-bottom:26px;}
  .eyebrow i{width:28px;height:1px;background:#CBD5E1;display:block;}
  .hero h1{font-weight:600;font-size:clamp(2.5rem,5.4vw,4.1rem);line-height:1.04;letter-spacing:-.035em;color:#0F172A;margin:0;max-width:16ch;text-wrap:balance;}
  .hero p{font-size:1.1rem;line-height:1.6;color:#64748B;max-width:600px;margin:22px auto 0;text-wrap:pretty;}

  .kicker{display:flex;align-items:center;justify-content:center;gap:11px;font:600 10px 'JetBrains Mono',monospace;letter-spacing:.24em;text-transform:uppercase;color:#94A3B8;margin:14px 0 6px;}
  .kicker i{width:44px;height:1px;background:#E2E8F0;display:block;}

  .carousel{position:relative;width:100%;height:400px;overflow:hidden;}
  .track{position:absolute;top:38px;left:50%;display:flex;align-items:flex-start;gap:28px;transition:transform .5s cubic-bezier(.22,.61,.36,1);}
  .card{flex:0 0 300px;width:300px;background:#FFF;border:1px solid #E2E8F0;border-radius:14px;overflow:hidden;cursor:pointer;
    transition:transform .5s cubic-bezier(.22,.61,.36,1),filter .5s ease,opacity .5s ease,box-shadow .25s ease,border-color .2s ease;}
  .card-preview{height:132px;background:#F8FAFC;border-bottom:1px solid #EEF2F6;position:relative;display:flex;align-items:center;justify-content:center;}
  .card-body{padding:20px 22px 22px;}
  .card-title{font-size:1.12rem;font-weight:600;color:#0F172A;letter-spacing:-.01em;}
  .card-desc{font-size:.82rem;line-height:1.55;color:#64748B;margin:8px 0 0;min-height:63px;}
  .card-foot{display:flex;align-items:center;justify-content:space-between;margin-top:14px;padding-top:14px;border-top:1px solid #F1F5F9;}
  .card-tag{font:600 9px 'JetBrains Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:#94A3B8;}
  .card-open{font:600 12px 'DM Sans',sans-serif;color:var(--accent);}
  .wl-row{display:flex;align-items:center;justify-content:space-between;font:600 11px 'JetBrains Mono',monospace;color:#475569;}

  .arrow{position:absolute;top:196px;transform:translateY(-50%);width:44px;height:44px;border-radius:50%;background:#FFF;border:1px solid #E2E8F0;cursor:pointer;
    display:flex;align-items:center;justify-content:center;color:#475569;font-size:20px;line-height:1;box-shadow:0 2px 10px rgba(15,23,42,.10);z-index:7;transition:all .2s ease;}
  .arrow:hover{border-color:var(--accent);color:var(--accent);box-shadow:0 4px 16px rgba(79,127,214,.24);}
  .arrow.l{left:calc(50% - 208px);} .arrow.r{left:calc(50% + 164px);}
  .dots{position:absolute;bottom:6px;left:0;right:0;display:flex;gap:8px;justify-content:center;z-index:7;}
  .dot{width:8px;height:8px;border-radius:4px;border:none;padding:0;background:#CBD5E1;cursor:pointer;transition:all .25s ease;}
  .dot.active{width:22px;background:var(--accent);}
  .hint{text-align:center;font-size:.78rem;color:#94A3B8;margin-top:2px;}

  .foot{max-width:1180px;margin:56px auto 0;padding:20px 32px 30px;}
  .foot-in{border-top:1px solid #E9EDF2;padding-top:20px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;}
  .foot-brand{font:700 11px 'JetBrains Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#475569;}
  .foot-meta{display:flex;gap:24px;font-size:.74rem;color:#94A3B8;}
</style></head>
<body>
  <div class="bar"><div class="bar-in">
    <div class="brand">__LOGO__<span class="divider"></span><span class="platform">Investment Intelligence Platform</span></div>
    <div style="display:flex;align-items:center;gap:22px;">
      <div class="clocks">
        <div class="clock"><div class="t" data-tz="America/New_York">--:--:--</div><div class="c">New York</div></div>
        <span class="vd"></span>
        <div class="clock"><div class="t" data-tz="Europe/London">--:--:--</div><div class="c">London</div></div>
        <span class="vd"></span>
        <div class="clock"><div class="t" data-tz="Africa/Johannesburg">--:--:--</div><div class="c">Johannesburg</div></div>
      </div>
      <div class="live"><span class="ring"><b></b><i></i></span><span>LIVE</span></div>
    </div>
  </div></div>

  <div class="ticker"><div class="ticker-track" data-ticker-track></div></div>

  <div class="hero">
    <div class="eyebrow"><i></i>Internal Platform &middot; Confidential<i></i></div>
    <h1>Investment intelligence, in one live view.</h1>
    <p>Markets, portfolio, holdings and alternative managers &mdash; continuously updated, and built for speed of interpretation.</p>
  </div>

  <div class="kicker"><i></i>Explore the workspaces &middot; 5 dashboards<i></i></div>

  <div class="carousel" data-carousel>
    <div class="track" data-track>__CARDS__</div>
    <button class="arrow l" data-prev aria-label="Previous">&lsaquo;</button>
    <button class="arrow r" data-next aria-label="Next">&rsaquo;</button>
    <div class="dots">__DOTS__</div>
  </div>
  <div class="hint">Use the arrows, dots or &larr; &rarr; keys to browse &middot; select the centre card to open it</div>

  <div class="foot"><div class="foot-in">
    <span class="foot-brand">Secco Capital</span>
    <div class="foot-meta"><span>Investment Intelligence Platform</span><span>Confidential</span><span>&copy; 2026</span></div>
  </div></div>

<script>
  var instruments = [
    {s:'S&P 500',v:6120.34,c:0.42,dec:2},{s:'Nasdaq 100',v:22480.9,c:0.61,dec:1},
    {s:'Russell 2000',v:2310.55,c:-0.18,dec:2},{s:'US 10Y',v:4.283,c:2,dec:3,mode:'bp'},
    {s:'Gold',v:3412.8,c:0.55,dec:1},{s:'Brent',v:71.20,c:-0.90,dec:2},
    {s:'Bitcoin',v:68240,c:1.24,dec:0},{s:'VIX',v:13.82,c:-2.10,dec:2},
    {s:'EUR/USD',v:1.0912,c:0.12,dec:4},{s:'USD/ZAR',v:18.047,c:-0.34,dec:3},
    {s:'DXY',v:104.21,c:0.08,dec:2},{s:'Copper',v:4.618,c:0.71,dec:3}
  ];
  function fmtVal(it){var val=it.v.toLocaleString('en-US',{minimumFractionDigits:it.dec,maximumFractionDigits:it.dec});return it.mode==='bp'?val+'%':val;}
  function chgTxt(it){if(it.mode==='bp'){var r=Math.round(it.c);return (r>=0?'+':'')+r+'bp';}return (it.c>=0?'\u25B2 ':'\u25BC ')+Math.abs(it.c).toFixed(2)+'%';}
  function chgCol(it){return it.c>=0?'#16A34A':'#DC2626';}
  function itemHTML(it){return '<div class="tk"><span class="s">'+it.s+'</span><span class="v" data-val data-sym="'+it.s+'">'+fmtVal(it)+
    '</span><span class="g" data-chg data-sym="'+it.s+'" style="color:'+chgCol(it)+'">'+chgTxt(it)+'</span></div>';}
  (function(){var one=instruments.map(itemHTML).join('');document.querySelector('[data-ticker-track]').innerHTML=one+one;})();
  setInterval(function(){
    var it=instruments[Math.floor(Math.random()*instruments.length)];
    it.v=it.v*(1+(Math.random()-0.5)*0.0009);
    it.c += it.mode==='bp' ? (Math.random()-0.5)*1.2 : (Math.random()-0.5)*0.14;
    var sel='[data-sym="'+it.s+'"]';
    document.querySelectorAll(sel+'[data-val]').forEach(function(el){el.textContent=fmtVal(it);
      el.style.background=it.c>=0?'rgba(22,163,74,0.14)':'rgba(220,38,38,0.12)';setTimeout(function(){el.style.background='transparent';},550);});
    document.querySelectorAll(sel+'[data-chg]').forEach(function(el){el.textContent=chgTxt(it);el.style.color=chgCol(it);});
  },2600);

  function tick(){document.querySelectorAll('[data-tz]').forEach(function(el){try{
    el.textContent=new Date().toLocaleTimeString('en-GB',{hour12:false,timeZone:el.getAttribute('data-tz')});}catch(e){}});}
  tick();setInterval(tick,1000);

  var cur=0,step=328;
  var cards=Array.prototype.slice.call(document.querySelectorAll('[data-card]'));
  var dots=Array.prototype.slice.call(document.querySelectorAll('[data-dot]'));
  var track=document.querySelector('[data-track]');var n=cards.length;
  function render(){
    track.style.transform='translateX('+(-(150+cur*step))+'px)';
    cards.forEach(function(c,i){var a=i===cur;c.style.opacity=a?'1':'0.4';c.style.transform=a?'scale(1)':'scale(0.82)';
      c.style.filter=a?'none':'blur(2.5px)';c.style.boxShadow=a?'0 20px 44px rgba(15,23,42,0.15)':'0 2px 8px rgba(15,23,42,0.05)';
      c.style.zIndex=a?'3':'1';c.style.borderColor=a?'#DCE3EC':'#E2E8F0';});
    dots.forEach(function(d,i){d.classList.toggle('active',i===cur);});
  }
  function go(i){cur=(i+n)%n;render();}
  render();
  document.querySelector('[data-prev]').addEventListener('click',function(){go(cur-1);});
  document.querySelector('[data-next]').addEventListener('click',function(){go(cur+1);});
  dots.forEach(function(d,i){d.addEventListener('click',function(){go(i);});});
  cards.forEach(function(c,i){c.addEventListener('click',function(){
    if(i!==cur){go(i);return;}
    var href=c.getAttribute('data-href');
    // Sandboxed component iframe: open the Streamlit page in a new tab against the parent origin.
    try{href=window.top.location.origin+href;}catch(e){}
    window.open(href,'_blank');
  });});
  var carousel=document.querySelector('[data-carousel]');var auto=null;
  function startAuto(){auto=setInterval(function(){go(cur+1);},6500);}
  startAuto();
  carousel.addEventListener('mouseenter',function(){clearInterval(auto);});
  carousel.addEventListener('mouseleave',function(){clearInterval(auto);startAuto();});
  window.addEventListener('keydown',function(e){if(e.key==='ArrowLeft')go(cur-1);else if(e.key==='ArrowRight')go(cur+1);});
</script>
</body></html>
"""

html = (
    PAGE.replace("__ACCENT__", ACCENT)
        .replace("__LOGO__", logo_img)
        .replace("__CARDS__", cards_html)
        .replace("__DOTS__", dots_html)
)

components.html(html, height=1180, scrolling=False)
