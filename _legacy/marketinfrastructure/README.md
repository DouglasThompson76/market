# MarketInfrastructure

`marketinfrastructure` is the **premarket setup engine** for the project.

For the operator-facing guide, see [USER_GUIDE.md](./USER_GUIDE.md).

It uses:

- `MarketSnapshot_output.csv` as the canonical ranking table, including embedded GNN columns
- `snapshot/` as the 90-day structural reference engine
- embedded news enrichment in `MarketSnapshot_output.csv` when available:
  - `newssentiment`
  - `newscore`

This app is intentionally **Phase 1 only**.

It prepares the watchlist before the bell by scoring:

- Pink Line resistance context
- HTF squeeze / compression
- Blue Sky / overhead resistance
- embedded narrative strength
- 90-day pattern intelligence

It does **not** confirm intraday timing or execute trades. A separate external system owns the minute-by-minute open logic.

## Run the app

```powershell
python -m marketinfrastructure
```

Then open `http://127.0.0.1:8050`.

## Run a data check

```powershell
python -m marketinfrastructure --check
```

## Core outputs

The premarket board ranks candidates with setup-oriented fields such as:

- `setup_priority`
- `setup_status`
- `pink_line_context`
- `squeeze_context`
- `blue_sky_context`
- `narrative_context`
- `pattern_context`
- `manual_open_checklist`
- `handoff_message`

## Embedded news transition

During the transition period, the app handles missing `newssentiment` and `newscore` gracefully:

- candidates still load and rank
- narrative is marked incomplete
- the setup may be downgraded to `NEEDS_REVIEW`

Once the news columns are populated in `MarketSnapshot_output.csv`, they become the primary catalyst source for Phase 1.

## Phase 2 handoff

After the open, hand the best candidates to the separate intraday system for:

- minute-by-minute breakout timing
- opening-range confirmation
- live volume/VWAP checks
- execution logic
