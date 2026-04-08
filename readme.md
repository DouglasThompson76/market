# GNN Market Intelligence Suite

Pre-market trading tools for traders, focused on turning daily snapshot data
into a ranked watchlist with explainable setup quality.

## What The Project Does

The current app is a lightweight FastAPI service with a browser UI for:

- Daily watchlist generation from `MarketSnapshot_output.csv`
- Pattern intelligence for structural setup classification
- Prior-day validator checks using daily proxies for breakout quality
- Backfilled forward expectancy by setup family, category, and validator profile
- Watchlist trade planning with target entry, take profit, and stop loss prices
- Symbol research and relationship-aware chat through the market engine

## Current Modules

- `app.py`: FastAPI entrypoint and API routes
- `core/daily_edge.py`: daily candidate engine, pattern logic, validator checks, expectancy, and trade-plan calculations
- `core/engine.py`: data loading and graph-aware market context
- `core/agent.py`: chat orchestration over the shared market engine
- `interface/index.html`: watchlist and intelligence UI
- `tests/test_daily_edge.py`: fixture and smoke coverage for the daily edge flow
- `marketautoresearch/program_concept.md`: concept note for future research tooling

## Data Layout

The app expects large local runtime artifacts:

- `MarketSnapshot_output.csv`
- `snapshot/stock_snapshot_YYYY-MM-DD.csv`
- `edge/edges_*.csv`
- `model/*.pt`

These files are intentionally ignored by git by default. They are part of the
local trading environment rather than the lightweight source repository.

## Environment Setup

### PowerShell

```powershell
.\initialise.bat
.\.venv\Scripts\Activate.ps1
```

### Manual Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Running The App

Run from the repository root so the relative data paths resolve correctly.

```powershell
uvicorn app:app --reload
```

Or:

```powershell
python app.py
```

The UI is served at `http://127.0.0.1:8000/`.

## Running Tests

```powershell
python -m unittest tests.test_daily_edge
```

The fixture suite runs without the large production datasets. The smoke test
will automatically skip if the local root snapshot or historical snapshot files
are not available.

## Repository Layout

```text
market/
|-- app.py
|-- core/
|-- interface/
|-- tests/
|-- marketautoresearch/
|-- snapshot/
|-- edge/
|-- model/
|-- initialise.bat
`-- requirements.txt
```

## Near-Term Roadmap

- Snapshot EDA workspace
- Market Patterns workspace
- More expectancy-aware watchlist refinement
- Additional trader review and journaling loops

## Contributing

See `CONTRIBUTING.md` for local setup, testing expectations, and PR guidance.
