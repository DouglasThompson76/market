# Pattern Intelligence Guide

This guide explains how pattern identification works in `marketinfrastructure` today.

## Entry Point

The pattern identification entry point is:

- [patterns.py](C:/Temp/Projects/market/_legacy/marketinfrastructure/patterns.py)
  `build_pattern_context(...)`

This function is called from:

- [service.py](C:/Temp/Projects/market/_legacy/marketinfrastructure/service.py)
  `MarketInfrastructureService._build_candidate(...)`

After all candidates are built, the app also calls:

- [patterns.py](C:/Temp/Projects/market/_legacy/marketinfrastructure/patterns.py)
  `attach_pattern_peers(...)`

That second step groups candidates into pattern families and adds the `similar_setups_today` context.

## End-To-End Flow

The current flow is:

1. Load `MarketSnapshot_output.csv`.
2. Load the 90-day daily history from `snapshot/`.
3. Build historical metrics for each ticker/date.
4. Build each candidate in `service.py`.
5. Call `build_pattern_context(...)` with the ticker's local 90-day history and premarket-safe inputs.
6. Add the pattern result to `candidate.pattern_context`.
7. Call `attach_pattern_peers(...)` so same-family names can reference each other on the board.

## Inputs To The Pattern Engine

`build_pattern_context(...)` uses:

- `ticker_history`
- `historical_metrics`
- `current_price`
- `daily_rsi`
- `relative_volume_ratio`
- `blue_sky_context`

These are all derived from local daily data and premarket-safe context. The pattern engine does not use minute-level timing data.

## What The Pattern Engine Measures

The current implementation looks at the recent 90-day daily structure and computes a compact feature signature:

- 90-day resistance touch count
- 20-day range vs 90-day range compression
- current position inside the 90-day range
- distance from the 90-day high
- latest volume vs recent average volume
- RSI trend over the recent window
- whether blue-sky structure is already present

These features are stored inside:

- `candidate.pattern_context["feature_signature"]`

## Pattern Families

The current code classifies candidates into one of these families:

- `Coiled Breakout`
- `High-Ground Leader`
- `Pressure Builder`
- `Momentum Expansion`
- `Range Repair`
- `Insufficient History`

## Current Decision Rules

These are the current first-pass rules inside `build_pattern_context(...)`.

### `Coiled Breakout`

Assigned when all of the following are true:

- resistance touches over 90 days are at least `3`
- 20-day range / 90-day range compression ratio is `<= 0.45`
- current price is in the top `70%` of the 90-day range

Interpretation:

- price has repeatedly pressed a known ceiling
- volatility/range has tightened
- the stock is still holding near the upper part of its 90-day structure

### `High-Ground Leader`

Assigned when:

- `Blue Sky` context is already `PASS`
- current price is in the top `82%` of the 90-day range

Interpretation:

- the stock is already living high in its 90-day structure
- overhead resistance is limited

### `Pressure Builder`

Assigned when all of the following are true:

- resistance touches over 90 days are at least `2`
- current price is in the top `60%` of the 90-day range
- RSI trend over the recent lookback is improving or flat

Interpretation:

- price is repeatedly leaning on resistance
- momentum is not deteriorating

### `Momentum Expansion`

Assigned when:

- recent volume ratio is at least `1.1`
- daily RSI is at least `60`

Interpretation:

- the chart may not be as compressed as a classic coil
- but momentum and participation are expanding

### `Range Repair`

Fallback family when none of the stronger families match.

Interpretation:

- the stock is rebuilding structure
- it may still be tradable later, but it is not showing a stronger repeating pattern yet

### `Insufficient History`

Assigned when the local 90-day history or historical metrics are not sufficient to classify the setup.

## Pattern Score

The pattern engine also calculates a `pattern score` from `0` to `100`.

The current score is a weighted combination of:

- resistance touch count
- compression strength
- 90-day range position
- RSI strength
- participation / volume ratio

This score is used as:

- a dashboard column
- a detail-page metric
- a light ranking input in `setup_score`

## Confidence

The engine assigns:

- `HIGH`
- `MEDIUM`
- `LOW`

Current logic:

- `HIGH`: at least 60 days of history and pattern score `>= 72`
- `MEDIUM`: at least 40 days of history and pattern score `>= 50`
- `LOW`: everything else

In the candidate checks, confidence is mapped to:

- `HIGH -> PASS`
- `MEDIUM -> WATCH`
- `LOW -> FAIL`

## Where The Result Appears

The result is stored on each candidate in:

- `candidate.pattern_context`

This currently powers:

- the `Pattern` column on the main dashboard
- the `Pattern Intelligence` card on the detail page
- the `Pattern Intelligence` favor check

Key fields include:

- `family`
- `score`
- `confidence`
- `summary`
- `similar_setups_today`
- `feature_signature`

## Similar Setups Today

After all candidates are classified, `attach_pattern_peers(...)`:

- groups candidates by `pattern family`
- ranks them inside that family
- stores up to 3 sibling tickers in `similar_setups_today`
- stores the family size in `family_population`

This is meant to help the trader see whether a setup is isolated or part of a broader structural cluster that day.

## Current Limits

This is a first-pass pattern engine, not a trained forecasting model.

Important limits:

- it uses explicit structural rules, not a learned embedding model
- it does not estimate win rate or expectancy yet
- it does not compare against archived historical breakout outcomes yet
- it is only as good as the quality of the daily snapshot history

## Good Next Steps

Natural upgrades from here:

1. Store historical pattern snapshots and forward outcomes.
2. Add analog lookup: "show me the 5 most similar prior setups."
3. Add family-level win rate and expectancy, with sample size.
4. Cache pattern features so startup is faster.
5. Replace or augment the rule-based family assignment with clustering or nearest-neighbor similarity.
