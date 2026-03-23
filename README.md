# ◼ Market Dashboard

Institutional-quality daily macro and market snapshot built with Streamlit.  
Designed for speed of interpretation — one glance gives you rates, equities, commodities, crypto, credit, and vol.

---

## Project Structure

```
market-dashboard/
├── app.py                  # Streamlit entry point — layout and rendering
├── requirements.txt        # Python dependencies
├── src/
│   ├── __init__.py
│   ├── config.py           # Asset universe and data source configuration
│   ├── data_ingest.py      # Fetches raw data from Yahoo Finance and FRED
│   ├── data_process.py     # Computes metrics (latest, 1D, 1W, YTD)
│   └── viz_helpers.py      # Formatting, colors, Plotly chart builders
└── README.md
```

**Architecture:** Three clean layers — ingestion → processing → visualisation.  
Each layer is independently testable and replaceable.

---

## Quick Start (macOS)

### 1. Prerequisites

- Python 3.10+ (check with `python3 --version`)
- pip (comes with Python)

If you don't have Python 3.10+:
```bash
brew install python@3.12
```

### 2. Clone / Copy the Project

Place the `market-dashboard/` folder wherever you like.

### 3. Create a Virtual Environment

```bash
cd market-dashboard
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Set Up FRED API Key (Optional but Recommended)

The dashboard uses FRED for rates (Fed Funds Rate) and credit spreads (IG, HY, EM).  
Without a FRED key, those assets fall back to Yahoo Finance where available, or show "—".

1. Get a free API key: https://fred.stlouisfed.org/docs/api/api_key.html  
2. Set it:

```bash
export FRED_API_KEY="your_key_here"
```

To make it permanent, add to `~/.zshrc`:
```bash
echo 'export FRED_API_KEY="your_key_here"' >> ~/.zshrc
source ~/.zshrc
```

### 6. Run the Dashboard

```bash
streamlit run app.py
```

Opens at `http://localhost:8501` in your browser.

---

## Usage

- **Refresh data:** Click the "Refresh" button or the sidebar "🔄 Refresh Data"
- **Auto-cache:** Data is cached for 5 minutes to avoid hammering APIs
- **Sidebar:** Shows data source info and refresh controls

---

## Scheduling Daily Refresh (Cron)

The architecture separates data fetching from display, making scheduled runs straightforward.

### Option A: Cron + Streamlit (simplest)

Just keep Streamlit running and refresh manually or set the `ttl` cache to auto-expire.

### Option B: Cron Data Export Script

Create a `refresh.py` that calls the data layer and saves to a local file:

```python
# refresh.py — Run via cron, saves snapshot to disk
from src.data_ingest import fetch_all_data
from src.data_process import process_all
import pickle
from datetime import datetime

raw = fetch_all_data()
metrics = process_all(raw)
with open("data/snapshot.pkl", "wb") as f:
    pickle.dump({"raw": raw, "metrics": metrics, "ts": datetime.now()}, f)
```

Cron entry (runs at 06:30 every weekday):
```bash
crontab -e
# Add:
30 6 * * 1-5 cd /path/to/market-dashboard && /path/to/.venv/bin/python refresh.py
```

Then modify `app.py` to load from the pickle instead of fetching live.

---

## Deployment Options

### 1. Streamlit Community Cloud (Free, Easiest)

1. Push to a GitHub repo
2. Go to https://share.streamlit.io
3. Connect your repo, set `app.py` as the entry point
4. Add `FRED_API_KEY` in the Secrets section
5. Share the generated URL with your team

### 2. Run on a VPS / Cloud VM

```bash
# On the server:
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
```

Use a reverse proxy (nginx/caddy) for HTTPS and auth.

### 3. Docker

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

## Phase 2 — Future Improvements

1. **Add more asset classes:** FX pairs (DXY, EUR/USD), real estate (REITs), and ag commodities
2. **Historical comparison view:** Toggle between 1M / 3M / 6M / 1Y sparklines
3. **Alerts:** Colour-coded alerts when spreads widen beyond thresholds or VIX spikes
4. **Correlation heatmap:** Rolling correlations between major asset classes
5. **PDF/email snapshot:** Auto-generate a one-page PDF morning brief and email to the team
6. **Database layer:** Store daily snapshots in SQLite for historical lookback
7. **Authentication:** Add Streamlit auth or put behind Cloudflare Access for team-only access
8. **Performance:** Switch to async data fetching with `asyncio` + `aiohttp` for faster loads
9. **Economic calendar:** Overlay key macro events (FOMC, CPI, NFP) on charts
10. **Relative value charts:** Spread between assets (e.g. 10Y-5Y, Gold/Silver ratio)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Make sure venv is activated: `source .venv/bin/activate` |
| FRED data shows "—" | Set `FRED_API_KEY` environment variable |
| Yahoo Finance rate-limited | Wait a few minutes; the 5-min cache helps |
| Port 8501 in use | `streamlit run app.py --server.port 8502` |
| Stale data | Click Refresh or clear cache in sidebar |

---

## License

Internal tool. Not for redistribution.
