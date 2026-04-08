# Contributing

Thanks for contributing to the market toolkit.

## Before You Start

- Use Python 3.12 or newer.
- Create a virtual environment with `.\initialise.bat` or `python -m venv .venv`.
- Install dependencies from `requirements.txt`.
- Keep large local datasets out of git unless there is an explicit data-versioning plan.

## Local Workflow

1. Start the app with `uvicorn app:app --reload`.
2. Run tests with `python -m unittest tests.test_daily_edge`.
3. Keep changes focused and explain trading-impact clearly in PR descriptions.

## Pull Requests

- Describe the edge or workflow being improved.
- Call out any assumptions around data availability.
- Include test coverage for new scoring, validation, or expectancy logic.
- Mention UI changes with screenshots when the watchlist or detail panel changes.

## Data Notes

This project works with large local artifacts in:

- `MarketSnapshot_output.csv`
- `snapshot/`
- `edge/`
- `model/`

Those files are ignored by default because they are large runtime assets rather
than lightweight source files.
