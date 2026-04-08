from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

from .models import DailySnapshotPoint, HistoricalMetrics


MARKET_SNAPSHOT_REQUIRED_COLUMNS = (
    "ticker",
    "snapshot_date",
    "gnn_prob",
    "selected_category",
    "trading_action",
    "management_action",
    "risk_bucket",
    "top_influencer",
    "influence_type",
)

HISTORY_WINDOW_DAYS = 90


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def parse_float(value: str | float | None) -> float | None:
    if isinstance(value, float):
        return value
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


class MarketDataRepository:
    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.market_snapshot_path = self.project_root / "MarketSnapshot_output.csv"
        self.snapshot_dir = self.project_root / "snapshot"

    def load_market_snapshot_rows(self) -> list[dict[str, str]]:
        if not self.market_snapshot_path.exists():
            raise FileNotFoundError(
                f"Market snapshot file was not found: {self.market_snapshot_path}"
            )
        with self.market_snapshot_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing = [
                column
                for column in MARKET_SNAPSHOT_REQUIRED_COLUMNS
                if column not in (reader.fieldnames or [])
            ]
            if missing:
                raise ValueError(
                    "MarketSnapshot_output.csv is missing required columns: "
                    + ", ".join(missing)
                )
            return [dict(row) for row in reader]

    def load_history_by_ticker(
        self, trade_dates: set[date], window_size: int = HISTORY_WINDOW_DAYS
    ) -> dict[str, list[DailySnapshotPoint]]:
        if not trade_dates:
            return {}
        snapshot_files = []
        max_trade_date = max(trade_dates)
        for path in self.snapshot_dir.glob("stock_snapshot_*.csv"):
            suffix = path.stem.replace("stock_snapshot_", "")
            try:
                file_date = date.fromisoformat(suffix)
            except ValueError:
                continue
            if file_date <= max_trade_date:
                snapshot_files.append((file_date, path))
        snapshot_files.sort(key=lambda item: item[0])
        selected_files = snapshot_files[-window_size:]

        history: dict[str, list[DailySnapshotPoint]] = defaultdict(list)
        for file_date, path in selected_files:
            with path.open(newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    ticker = (row.get("ticker") or "").strip().upper()
                    if not ticker:
                        continue
                    history[ticker].append(
                        DailySnapshotPoint(
                            ticker=ticker,
                            snapshot_date=file_date,
                            day_close=parse_float(row.get("day_close")),
                            day_volume=parse_float(row.get("day_volume")),
                            day_high=parse_float(row.get("day_high")),
                            day_low=parse_float(row.get("day_low")),
                            high_20d=parse_float(row.get("high_20d")),
                            low_20d=parse_float(row.get("low_20d")),
                            vwap=parse_float(row.get("vwap")),
                            rsi14=parse_float(row.get("rsi14")),
                            ref_name=(row.get("ref_name") or "").strip() or None,
                            ref_industry=(row.get("ref_industry") or "").strip() or None,
                        )
                    )
        return history

    def build_historical_metrics(
        self, history_by_ticker: dict[str, list[DailySnapshotPoint]], trade_date: date
    ) -> dict[str, HistoricalMetrics]:
        metrics: dict[str, HistoricalMetrics] = {}
        for ticker, points in history_by_ticker.items():
            usable = [point for point in points if point.snapshot_date <= trade_date]
            if not usable:
                continue
            usable.sort(key=lambda point: point.snapshot_date)
            latest = usable[-1]
            last_5 = usable[-5:]
            last_20 = usable[-20:]
            last_90 = usable[-HISTORY_WINDOW_DAYS:]

            prior_high = latest.high_20d
            prior_low = latest.low_20d
            if prior_high is None:
                highs = [point.day_high for point in last_20 if point.day_high is not None]
                prior_high = max(highs) if highs else None
            if prior_low is None:
                lows = [point.day_low for point in last_20 if point.day_low is not None]
                prior_low = min(lows) if lows else None

            highs_90 = [point.day_high for point in last_90 if point.day_high is not None]
            resistance_90d = max(highs_90) if highs_90 else prior_high
            touch_count_90d = None
            if resistance_90d not in (None, 0):
                tolerance = resistance_90d * 0.015
                touch_count_90d = sum(
                    1
                    for point in last_90
                    if point.day_high is not None and point.day_high >= resistance_90d - tolerance
                )

            range_width = None
            range_position_pct = None
            if (
                latest.day_close is not None
                and prior_high is not None
                and prior_low is not None
                and prior_high != prior_low
            ):
                range_width = prior_high - prior_low
                range_position_pct = ((latest.day_close - prior_low) / range_width) * 100.0

            volumes = [point.day_volume for point in last_5 if point.day_volume is not None]
            metrics[ticker] = HistoricalMetrics(
                ticker=ticker,
                latest_snapshot_date=latest.snapshot_date,
                latest_close=latest.day_close,
                latest_volume=latest.day_volume,
                latest_vwap=latest.vwap,
                latest_rsi14=latest.rsi14,
                avg_volume_5d=mean(volumes) if volumes else None,
                resistance_20d=prior_high,
                resistance_90d=resistance_90d,
                touch_count_90d=touch_count_90d,
                prior_range_high=prior_high,
                prior_range_low=prior_low,
                prior_range_width=range_width,
                prior_range_position_pct=range_position_pct,
            )
        return metrics
