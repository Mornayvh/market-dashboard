# ◼ Secco Capital — Investment Intelligence Platform

A Streamlit multi-page platform for daily macro, portfolio and holdings analysis.
Designed for speed of interpretation — one glance gives you rates, equities,
commodities, credit, FX and vol, plus dedicated views for private holdings and
listed alternative managers.

---

## Pages

| Page | File | What it does |
|------|------|--------------|
| Home | `app.py` | Landing page — live clock, ticker strip and the dashboard carousel. Also hosts the light/dark theme toggle. |
| Market Dashboard | `pages/1_Market_Dashboard.py` | Daily macro snapshot: rates, equities, commodities, credit spreads, FX, volatility. |
| Partner Dashboard | `pages/2_Partner_Dashboard.py` | Allocations by geography, asset class, sector and stage. **Password-protected.** |
| Stock Watchlist | `pages/3_Stock_Watchlist.py` | Live prices for core, connected and global holdings across exchanges and currencies. |
| Direct Investments | `pages/4_Direct_Investments.py` | Public-market proxy tracker for private holdings — comps, sector ETFs, capex, sentiment. |
| Alt Managers | `pages/5_Alt_Managers.py` | Listed alternative managers compared as stocks — valuation, returns, risk. |

---

## Project Structure

```
market-dashboard/
├── app.py                      # Home page — topbar, ticker, hero, carousel
├── pages/                      # One file per dashboard (Streamlit auto-routes these)
├── export_pdf.py               # Market Dashboard -> PDF snapshot (standalone)
├── export_watchlist_pdf.py     # Stock Watchlist -> PDF snapshot (standalone)
├── requirements.txt
├── data/
│   ├── Internal_Investments_Dashboard.xlsx   # Partner Dashboard source
│   └── static/                 # Hand-maintained quarterly figures (see below)
├── scripts/
│   └── fetch_share_prices.py   # Ad-hoc: pull daily OHLC into an Excel workbook
└── src/
    ├── config.py               # Macro asset universe and data sources
    ├── data_ingest.py          # Raw fetches from Yahoo Finance and FRED
    ├── data_process.py         # Metrics (latest, 1D, 1W, LTM)
    ├── viz_helpers.py          # Formatting, colours, Plotly builders
    ├── theme.py                # Light/dark palette + the shared page stylesheet
    ├── watchlist.py            # The stock watchlist universe (single source of truth)
    ├── alt_managers/           # Alt-manager universe, fetchers, metrics, AUM reference
    └── direct_investments/     # Holdings config, loaders, view builders
```

**Architecture:** ingestion (`data_ingest`) → processing (`data_process`) →
presentation (pages + `viz_helpers`). The two larger dashboards own their own
subpackage under `src/` rather than pushing everything through the shared layer.

---

## Quick Start (macOS)

### 1. Prerequisites

- Python 3.10+ (check with `python3 --version`)

If you don't have it: `brew install python@3.12`

### 2. Virtual environment and dependencies

```bash
cd market-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. FRED API key (optional but recommended)

FRED supplies the Fed Funds Rate and the credit spreads (IG, HY, EM). Without a
key those rows show "—"; everything else still works off Yahoo Finance.

Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html, then:

```bash
echo 'export FRED_API_KEY="your_key_here"' >> ~/.zshrc
source ~/.zshrc
```

### 4. Partner Dashboard password (optional)

That page is gated. Set either a Streamlit secret:

```toml
# .streamlit/secrets.toml
[portfolio]
password = "your_password"
```

or the `PORTFOLIO_PASSWORD` environment variable. Without one, the page cannot
be opened.

### 5. Run

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Usage

- **Refresh:** each page has a Refresh control that clears its cache and reruns.
- **Caching:** TTLs are tuned per data type — 5 min for prices, 1 h for market
  caps and FX, 24 h for slow-moving fundamentals. Pages fetch live on load;
  there is no snapshot store.
- **Theme:** the toggle in the home-page topbar. The choice is written to
  `localStorage` and carried between pages on the `?theme=` query parameter, so
  it survives new tabs and browser restarts.

### PDF snapshots

Both exporters run standalone, without a Streamlit server:

```bash
python export_pdf.py                  # market_dashboard_<YYYY-MM-DD>.pdf
python export_watchlist_pdf.py        # stock_watchlist_<YYYY-MM-DD>.pdf
python export_pdf.py --out brief.pdf  # or pick the path
```

Generated PDFs are gitignored.

---

## Deployment

### Streamlit Community Cloud (current)

1. Push to the GitHub repo.
2. Entry point is `app.py`.
3. Add `FRED_API_KEY` and the `[portfolio]` password under Secrets.

**A push alone does not update the running app** — reboot it from the Streamlit
Cloud dashboard after deploying.

`.streamlit/config.toml` disables the inotify file-watcher, because the shared
host hits the OS watch limit at startup and crashes the app without it.

### VPS / Cloud VM

```bash
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
```

Put a reverse proxy (nginx/caddy) in front for HTTPS and auth.

### Docker

```Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
docker build -t market-dashboard .
docker run -p 8501:8501 -e FRED_API_KEY=your_key market-dashboard
```

---

## Theming and page styling

`src/theme.py` owns both.

- **Palette.** `LIGHT` and `DARK` dicts are published as `--tk-*` CSS custom
  properties. Page stylesheets reference the variables rather than hex literals,
  so one palette swap re-skins the platform. A few keys (`categorical`,
  `navy_scale`, …) are Plotly-only and never emitted as CSS.
- **Shared stylesheet.** `page_css(max_width)` returns the rules every page
  needs — font import, shell, chrome-hiding, buttons, the `.page-header` family
  and `.section-header`. Each page emits it first, then its own rules:

  ```python
  st.markdown("<style>" + page_css("1400px") + """
      .my-component { ... }
  </style>""", unsafe_allow_html=True)
  ```

  Page rules come after and so win on equal specificity — that is how Alt
  Managers tightens its header margin and Direct Investments widens its section
  spacing, each in one line.

  Data tables are deliberately **not** shared. They look alike but differ in
  alignment, type size and cell padding, so each page owns its own.

Call `apply_theme()` once per page, immediately after `st.set_page_config`.

---

## The stock watchlist universe

`src/watchlist.py` is the single source of truth, imported by both
`pages/3_Stock_Watchlist.py` and `export_watchlist_pdf.py`. Add or remove names
there only — the page and the PDF then stay in step automatically.

It holds `WATCHLIST` (group → list of `(name, ticker, currency)`),
`CURRENCY_SYMBOLS`, and `FULL_YEAR_MIN_DAYS` (the calendar span a 1-year fetch
must cover before LTM and 52-week figures are reported, so a recent listing
doesn't show a misleading full-year number).

---

## Updating Static Data (Direct Investments page)

The Direct Investments page mixes live market data (yfinance / FRED / Google
Trends) with hand-edited quarterly figures that can't be pulled for free. These
live as YAML in `data/static/` and need refreshing each quarter.

| File | Update when | Source |
|------|-------------|--------|
| `hyperscaler_capex.yaml` | After Alphabet/MSFT/META/AMZN earnings (Jan, Apr, Jul, Oct) | 10-Qs |
| `nvda_dc_revenue.yaml` | After NVDA earnings (Feb, May, Aug, Nov) | NVDA earnings release |
| `neocloud_capex.yaml` | After CoreWeave & Nebius earnings | 10-Qs |
| `fda_nme_approvals.yaml` | Annually, around Feb | FDA CDER Novel Drug Approvals page |

### How to update

1. Open the relevant YAML file in `data/static/`.
2. **Quarterly schema** (`hyperscaler_capex`, `nvda_dc_revenue`, `neocloud_capex`):
   remove the oldest entry under `quarters:` (keeps the chart at 8 quarters) and
   append the latest reported quarter.
3. **Annual schema** (`fda_nme_approvals`): append a new entry under `periods:`.
4. Update `last_updated:` and add a one-line note under `sources:` citing the
   filing or page used.
5. Commit, push, then reboot the app on Streamlit Cloud.

Each chart shows its `last_updated` date as a caption, so stale data is visible
at a glance.

Holdings currently tracked, configured in `src/direct_investments/config.py`:
Novolex, Kelvion, Real Chemistry, SAP Fioneer, Asia Restaurants.

---

## Alternative Asset Managers page

`pages/5_Alt_Managers.py`, backed by `src/alt_managers/`, compares **9** listed
alternative asset managers **as stocks**, using Yahoo Finance plus a small
hand-maintained AUM table. No paid APIs, no scraping.

- `universe.py` — the tracked universe (name, category, geo, tilt, currency):
  Blackstone, KKR, Apollo, Carlyle, Brookfield AM, TPG, EQT AB, CVC Capital,
  Partners Group.
- `data.py` — cached yfinance fetchers, FX normalisation to USD, per-ticker
  failed-field tracking.
- `metrics.py` — return and risk calcs (YTD, 1Y, 3Y/5Y annualised, max drawdown,
  annualised vol).
- `reference_data.py` — hand-maintained **Total AUM** per manager, which Yahoo
  does not carry. Refresh quarterly: update `total_aum_usd_bn`, `as_of` and
  `source` per ticker; set the figure to `None` where a firm reports no
  comparable Total-AUM number and the page renders "—". The seeded figures are
  approximate and flagged as needing verification against primary disclosures.

### Known limitations

- **Yahoo data is unofficial** — fields may be stale or missing without warning.
  Missing values render blank and are listed in the in-app *Data quality* panel;
  nothing is fabricated or interpolated.
- **Forward P/E is unreliable here** — it is based on GAAP EPS, not the FRE or
  Distributable Earnings these firms guide on, and is often missing entirely for
  the European listings.
- **This compares them as _stocks_, not as businesses** — beyond the AUM
  reference table there is no FRE, perpetual-capital, fundraising or accrued-carry
  data, none of which is available free.
- **Currency** — market caps are converted to USD at latest spot FX; prices stay
  native. Recently-listed names (CVC, EQT) show blank for longer return windows.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Activate the venv: `source .venv/bin/activate` |
| FRED rows show "—" | Set `FRED_API_KEY` |
| Partner Dashboard won't open | Set the `[portfolio]` secret or `PORTFOLIO_PASSWORD` |
| Yahoo Finance rate-limited | Wait a few minutes; the caches help |
| Port 8501 in use | `streamlit run app.py --server.port 8502` |
| Stale data | Use the page's Refresh control |
| Pushed but nothing changed | Reboot the app in the Streamlit Cloud dashboard |
| `inotify watch limit reached` | Already handled by `fileWatcherType = "none"` in `.streamlit/config.toml` |

---

## Possible Improvements

1. **More asset classes:** REITs and ag commodities on the Market Dashboard
2. **Historical comparison:** toggle 1M / 3M / 6M / 1Y sparkline windows
3. **Alerts:** flag spreads widening past a threshold, or a VIX spike
4. **Correlation heatmap:** rolling correlations across asset classes
5. **Database layer:** store daily snapshots for historical lookback
6. **Authentication:** platform-wide auth rather than the single gated page
7. **Performance:** async fetching (`asyncio` + `aiohttp`) to cut load times
8. **Economic calendar:** overlay FOMC, CPI and NFP dates on charts
9. **Relative value:** spread charts (10Y-5Y, Gold/Silver)

---

## License

Internal tool. Not for redistribution.
