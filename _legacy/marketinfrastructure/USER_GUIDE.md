# MarketInfrastructure User Guide

`marketinfrastructure` is the Phase 1 premarket setup engine for this project.

It is designed to help a trader build the watchlist before the open by combining:

- `MarketSnapshot_output.csv`
- the 90-day daily history in `snapshot/`
- embedded ML/GNN context
- embedded news context when `newssentiment` and `newscore` are populated

This app does **not** confirm intraday timing. A separate Phase 2 system owns minute-by-minute trigger confirmation after the open.

For a focused explanation of the pattern engine, see [PATTERN_INTELLIGENCE_GUIDE.md](C:/Temp/Projects/market/_legacy/marketinfrastructure/PATTERN_INTELLIGENCE_GUIDE.md).

## What The App Does

The app ranks candidates before the bell using:

- GNN confidence from `MarketSnapshot_output.csv`
- Pink Line resistance context
- HTF squeeze / compression context
- Blue Sky / overhead resistance context
- narrative strength from embedded news columns when available
- 90-day pattern intelligence from the local daily history

The goal is to help the trader answer:

- Which names deserve attention this morning?
- What kind of setup does each name resemble?
- How close is the stock to a valid structural breakout?

## How To Run It

From the project root:

```powershell
python -m marketinfrastructure
```

Then open:

`http://127.0.0.1:8050`

To run a data-only check:

```powershell
python -m marketinfrastructure --check
```

## Main Dashboard

The main screen is the **Premarket Setup Board**.

It shows a ranked candidate table with these columns:

- `Symbol`
- `Price`
- `Priority`
- `Setup`
- `GNN`
- `Pattern`
- `News`
- `Pink Line`
- `Squeeze`
- `Blue Sky`
- `Risk`

### Sorting

You can sort the table by clicking any column header.

- Clicking a header sorts by that column
- Clicking the same header again toggles ascending / descending
- Current filters and row limit are preserved while sorting

### Filters

The left sidebar supports:

- ticker/company search
- category filter
- action filter
- risk bucket filter
- setup status filter
- row limit

## Candidate Detail Screen

Click any ticker to open the **Premarket Setup Review** page.

This screen is organized for human review and includes:

- trade context
- premarket structure
- narrative and handoff
- pattern intelligence
- premarket checks
- manual follow-through checklist
- diagnostics sections

## Pattern Intelligence

The app now includes a first-pass 90-day pattern engine.

It looks at the recent daily structure and classifies the setup into trader-readable families such as:

- `Coiled Breakout`
- `High-Ground Leader`
- `Pressure Builder`
- `Momentum Expansion`
- `Range Repair`

For each candidate, the app shows:

- `Pattern family`
- `Pattern score`
- `Confidence`
- `Similar setups today`

This is meant to help the trader quickly understand whether the chart is showing a repeating structural pattern, not just a one-off snapshot score.

## Setup Status Meanings

- `HIGH_PRIORITY_SETUP`: strongest names on the board
- `WATCHLIST`: worth monitoring, but not the very best setups
- `NEEDS_REVIEW`: mixed context or incomplete narrative; trader review required
- `NOT_READY`: not a core premarket focus

Names with `REDUCE` or `EXIT` actions are intentionally pushed out of the actionable setup flow.

## How A Trader Can Use It

Typical premarket workflow:

1. Open the board before 9:30 AM.
2. Filter for `BUY`, `ADD`, or other preferred actions.
3. Sort by `Pattern`, `GNN`, `Price`, or structural columns depending on the morning's focus.
4. Open the strongest names and review:
   resistance interaction
   squeeze quality
   blue-sky condition
   narrative context
   pattern family and score
5. Build the final watchlist.
6. Hand the best names to the separate intraday system after the open.

## Data Notes

- `MarketSnapshot_output.csv` is the canonical ranking table
- `snapshot/` provides the 90-day structural history
- the app handles missing `newssentiment` and `newscore` gracefully
- when news columns are missing, narrative is marked incomplete rather than guessed

## API

The app exposes a local JSON candidate endpoint:

`/api/candidates`

It accepts the same filtering and sorting query parameters as the main dashboard.

## Important Limits

- This app is **premarket only**
- It does not compute opening-range breakout timing
- It does not confirm live VWAP/volume timing
- It does not place trades
- It does not replace the separate intraday system

## Performance Note

The app loads the full 90-day snapshot history to build the premarket board.

That makes startup and `--check` slower than a lightweight screener. On the current dataset, a full load may take a few minutes.

## After Code Changes

If the app is already running and the code changes, restart the server process to load the latest logic and UI updates.
