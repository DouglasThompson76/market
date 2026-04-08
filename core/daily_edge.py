from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any


ACTION_SCORES = {
    "BUY": 1.0,
    "ADD": 0.85,
    "HOLD": 0.55,
    "WATCH_ONLY": 0.35,
    "REDUCE": 0.05,
    "EXIT": 0.0,
}

CATEGORY_RISK_PROFILES = {
    "DAY TRADER (INTRADAY)": {"stop_buffer_mult": 0.55, "reward_multiple": 1.25},
    "AGGRESSIVE BREAKOUTS": {"stop_buffer_mult": 0.85, "reward_multiple": 2.2},
    "BALANCED MOMENTUM": {"stop_buffer_mult": 0.75, "reward_multiple": 1.8},
    "HIGH PROFIT GROWTH": {"stop_buffer_mult": 1.0, "reward_multiple": 2.5},
    "HIGH-BETA SPECULATIVE": {"stop_buffer_mult": 1.25, "reward_multiple": 2.0},
    "STEADY COMPOUNDERS": {"stop_buffer_mult": 0.65, "reward_multiple": 1.6},
    "ULTRA-CONSERVATIVE": {"stop_buffer_mult": 0.5, "reward_multiple": 1.3},
}

SETUP_STATUS_ORDER = {
    "HIGH_PRIORITY_SETUP": 0,
    "WATCHLIST": 1,
    "NEEDS_REVIEW": 2,
    "NOT_READY": 3,
}

VALIDATOR_STATUS_ORDER = {
    "PASS": 0,
    "WATCH": 1,
    "FAIL": 2,
}

VALIDATOR_WEIGHTS = {
    "breakout_proxy": 30.0,
    "above_vwap": 10.0,
    "relative_volume": 15.0,
    "relative_strength_price": 25.0,
    "relative_strength_rsi": 20.0,
}

SECTOR_ETF_RULES = (
    ("XLK", ("software", "semiconductor", "internet", "technology", "it services", "hardware")),
    ("XLF", ("bank", "financial", "insurance", "capital markets", "asset management", "credit")),
    ("XLE", ("oil", "gas", "energy", "exploration", "drilling", "midstream")),
    ("XLV", ("biotech", "pharma", "health", "medical", "care", "life sciences")),
    ("XLI", ("aerospace", "defense", "industrial", "transport", "machinery", "logistics", "airline")),
    ("XLY", ("retail", "consumer discretionary", "auto", "restaurant", "travel", "leisure", "apparel")),
    ("XLP", ("food", "beverage", "household", "consumer staples", "tobacco", "personal products")),
    ("XLB", ("chemical", "materials", "mining", "steel", "metals", "paper", "construction materials")),
    ("XLU", ("utility", "utilities", "power", "water")),
    ("XLRE", ("reit", "real estate", "property")),
    ("XLC", ("telecom", "media", "communication", "streaming", "advertising", "entertainment")),
)

MIN_EXPECTANCY_SAMPLES = 8
LOOKBACK_DAYS = 90
EXPECTANCY_HORIZONS = (2, 5, 10)


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def parse_float(value: str | float | int | None) -> float | None:
    if isinstance(value, (float, int)):
        return float(value)
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def safe_round(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def pct_change(current: float | None, reference: float | None) -> float | None:
    if current in (None, 0) or reference in (None, 0):
        return None
    return ((current / reference) - 1.0) * 100.0


@dataclass(slots=True)
class DailySnapshotPoint:
    ticker: str
    snapshot_date: date
    day_close: float | None
    day_volume: float | None
    day_high: float | None
    day_low: float | None
    high_20d: float | None
    low_20d: float | None
    vwap: float | None
    rsi14: float | None
    ref_name: str | None
    ref_industry: str | None


@dataclass(slots=True)
class HistoricalMetrics:
    ticker: str
    latest_snapshot_date: date | None
    latest_close: float | None
    latest_volume: float | None
    latest_vwap: float | None
    latest_rsi14: float | None
    avg_volume_5d: float | None
    resistance_20d: float | None
    support_20d: float | None
    resistance_50d: float | None
    support_50d: float | None
    resistance_90d: float | None
    support_90d: float | None
    touch_count_90d: int | None
    return_5d_pct: float | None
    return_20d_pct: float | None
    range_position_day_pct: float | None
    avg_daily_range_14d: float | None
    avg_daily_range_20d: float | None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.latest_snapshot_date is not None:
            payload["latest_snapshot_date"] = self.latest_snapshot_date.isoformat()
        return payload


@dataclass(slots=True)
class CandidateRecord:
    symbol: str
    trade_date: date
    company_name: str | None
    industry: str | None
    selected_category: str | None
    trading_action: str | None
    gnn_prob: float | None
    trend_score: float | None
    risk_bucket: str | None
    current_price: float | None
    resistance_20d: dict[str, Any]
    relative_volume_context: dict[str, Any]
    daily_rsi_context: dict[str, Any]
    benchmark_context: dict[str, Any]
    pattern_context: dict[str, Any]
    validator_context: dict[str, Any]
    expectancy_context: dict[str, Any]
    trade_plan_context: dict[str, Any]
    setup_score: float
    setup_status: str
    structural_score: float
    historical_metrics: dict[str, Any]
    raw_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "symbol": self.symbol,
            "ticker": self.symbol,
            "trade_date": self.trade_date.isoformat(),
            "date": self.trade_date.isoformat(),
            "company_name": self.company_name,
            "industry": self.industry,
            "selected_category": self.selected_category,
            "trading_action": self.trading_action,
            "gnn_prob": self.gnn_prob,
            "trend_score": self.trend_score,
            "risk_bucket": self.risk_bucket,
            "current_price": self.current_price,
            "resistance_20d": self.resistance_20d,
            "relative_volume_context": self.relative_volume_context,
            "daily_rsi_context": self.daily_rsi_context,
            "benchmark_context": self.benchmark_context,
            "pattern_context": self.pattern_context,
            "validator_context": self.validator_context,
            "expectancy_context": self.expectancy_context,
            "trade_plan_context": self.trade_plan_context,
            "setup_score": self.setup_score,
            "setup_status": self.setup_status,
            "structural_score": self.structural_score,
            "historical_metrics": self.historical_metrics,
            "expectancy_5d": self.expectancy_context.get("horizons", {}).get("5d", {}).get("avg_end_return_pct"),
            "expectancy_sample_size": self.expectancy_context.get("sample_size"),
            "target_entry_price": self.trade_plan_context.get("target_entry_price"),
            "take_profit_price": self.trade_plan_context.get("take_profit_price"),
            "stop_loss_price": self.trade_plan_context.get("stop_loss_price"),
        }
        return payload


def build_pattern_context(
    *,
    ticker_history: list[DailySnapshotPoint],
    historical_metrics: HistoricalMetrics | None,
    current_price: float | None,
    daily_rsi: float | None,
    relative_volume_ratio: float | None,
) -> dict[str, Any]:
    usable = sorted(ticker_history, key=lambda point: point.snapshot_date)[-LOOKBACK_DAYS:]
    if not usable or historical_metrics is None:
        return {
            "family": "Insufficient History",
            "score": None,
            "confidence": "LOW",
            "summary": "The pattern engine needs more daily history before it can classify this setup.",
            "similar_setups_today": [],
            "family_population": None,
            "feature_signature": {},
        }

    highs_90 = [point.day_high for point in usable if point.day_high is not None]
    lows_90 = [point.day_low for point in usable if point.day_low is not None]
    highs_20 = [point.day_high for point in usable[-20:] if point.day_high is not None]
    lows_20 = [point.day_low for point in usable[-20:] if point.day_low is not None]
    volumes_20 = [point.day_volume for point in usable[-20:] if point.day_volume is not None]
    rsi_10 = [point.rsi14 for point in usable[-10:] if point.rsi14 is not None]

    high_90 = max(highs_90) if highs_90 else None
    low_90 = min(lows_90) if lows_90 else None
    high_20 = max(highs_20) if highs_20 else None
    low_20 = min(lows_20) if lows_20 else None

    range_90 = None if high_90 is None or low_90 is None else high_90 - low_90
    range_20 = None if high_20 is None or low_20 is None else high_20 - low_20
    compression_ratio = (
        None if range_90 in (None, 0) or range_20 is None else range_20 / range_90
    )

    range_position_90 = None
    if current_price is not None and range_90 not in (None, 0) and low_90 is not None:
        range_position_90 = ((current_price - low_90) / range_90) * 100.0

    close_to_90_high_pct = pct_change(current_price, high_90)
    avg_volume_20 = mean(volumes_20) if volumes_20 else None
    volume_ratio_20 = (
        None
        if historical_metrics.latest_volume in (None, 0) or avg_volume_20 in (None, 0)
        else historical_metrics.latest_volume / avg_volume_20
    )
    if volume_ratio_20 is None:
        volume_ratio_20 = relative_volume_ratio

    avg_rsi_10 = mean(rsi_10) if rsi_10 else None
    rsi_trend = None if daily_rsi is None or avg_rsi_10 is None else daily_rsi - avg_rsi_10
    touch_count = historical_metrics.touch_count_90d or 0

    family = "Range Repair"
    summary = "The setup is rebuilding structure inside its 90-day range."
    if (
        touch_count >= 3
        and compression_ratio is not None
        and compression_ratio <= 0.45
        and range_position_90 is not None
        and range_position_90 >= 70
    ):
        family = "Coiled Breakout"
        summary = "Repeated tests near resistance plus a compressed 90-day range suggest a coiled breakout."
    elif range_position_90 is not None and range_position_90 >= 82:
        family = "High-Ground Leader"
        summary = "The stock is living at the upper end of its 90-day range with limited overhead supply."
    elif (
        touch_count >= 2
        and range_position_90 is not None
        and range_position_90 >= 60
        and (rsi_trend or 0.0) >= 0
    ):
        family = "Pressure Builder"
        summary = "The chart is leaning on resistance while momentum is stable to improving."
    elif (volume_ratio_20 or 0.0) >= 1.1 and (daily_rsi or 0.0) >= 60:
        family = "Momentum Expansion"
        summary = "Participation and momentum are expanding across the recent structure."

    score = 0.0
    score += min(touch_count, 5) / 5.0 * 24.0
    if compression_ratio is not None:
        score += max(0.0, min((1.0 - compression_ratio) * 28.0, 24.0))
    if range_position_90 is not None:
        score += max(0.0, min(range_position_90 / 100.0 * 22.0, 22.0))
    if daily_rsi is not None:
        score += max(0.0, min((daily_rsi - 40.0) / 30.0 * 16.0, 16.0))
    if volume_ratio_20 is not None:
        score += max(0.0, min((volume_ratio_20 - 0.7) / 0.8 * 14.0, 14.0))
    score = max(0.0, min(score, 100.0))

    confidence = "LOW"
    if len(usable) >= 60 and score >= 72:
        confidence = "HIGH"
    elif len(usable) >= 40 and score >= 50:
        confidence = "MEDIUM"

    return {
        "family": family,
        "score": round(score, 2),
        "confidence": confidence,
        "summary": summary,
        "similar_setups_today": [],
        "family_population": None,
        "feature_signature": {
            "touch_count_90d": touch_count,
            "compression_ratio": safe_round(compression_ratio, 3),
            "range_position_90d_pct": safe_round(range_position_90),
            "close_to_90d_high_pct": safe_round(close_to_90_high_pct),
            "volume_ratio_20d": safe_round(volume_ratio_20),
            "rsi_trend_10d": safe_round(rsi_trend),
            "avg_volume_20d": safe_round(avg_volume_20),
            "days_in_window": len(usable),
        },
    }


def attach_pattern_peers(candidates: list[CandidateRecord]) -> None:
    grouped: dict[str, list[CandidateRecord]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.pattern_context.get("family", "Unknown")].append(candidate)

    for members in grouped.values():
        ranked = sorted(
            members,
            key=lambda candidate: (
                -(candidate.pattern_context.get("score") or 0.0),
                -(candidate.gnn_prob or 0.0),
                candidate.symbol,
            ),
        )
        peer_symbols = [candidate.symbol for candidate in ranked]
        population = len(ranked)
        for candidate in ranked:
            candidate.pattern_context["family_population"] = population
            candidate.pattern_context["similar_setups_today"] = [
                symbol for symbol in peer_symbols if symbol != candidate.symbol
            ][:3]


class DailyEdgeService:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.market_snapshot_path = self.project_root / "MarketSnapshot_output.csv"
        self.snapshot_dir = self.project_root / "snapshot"
        self._candidates: list[CandidateRecord] = []
        self.refresh()

    def refresh(self) -> None:
        rows = self._load_market_snapshot_rows()
        history_by_ticker = self._load_history_by_ticker()
        benchmark_history = self._build_benchmark_history(history_by_ticker)
        benchmark_metric_cache = self._build_benchmark_metric_cache(benchmark_history)
        row_by_ticker = {
            (row.get("ticker") or "").strip().upper(): row
            for row in rows
            if (row.get("ticker") or "").strip()
        }
        expectancy_maps = self._build_expectancy_maps(
            row_by_ticker,
            history_by_ticker,
            benchmark_metric_cache,
        )

        candidates: list[CandidateRecord] = []
        for row in rows:
            ticker = (row.get("ticker") or "").strip().upper()
            trade_date = parse_date(row.get("snapshot_date"))
            if not ticker or trade_date is None:
                continue
            history = history_by_ticker.get(ticker, [])
            usable = [point for point in history if point.snapshot_date <= trade_date]
            metrics = self._build_historical_metrics(ticker, usable)
            candidate = self._build_candidate(
                snapshot_row=row,
                history=usable,
                historical_metrics=metrics,
                benchmark_metric_cache=benchmark_metric_cache,
                expectancy_maps=expectancy_maps,
            )
            candidates.append(candidate)

        attach_pattern_peers(candidates)
        for candidate in candidates:
            candidate.expectancy_context = self._select_expectancy_context(
                pattern_family=candidate.pattern_context.get("family"),
                category=candidate.selected_category,
                validator_profile=candidate.validator_context.get("validator_profile"),
                expectancy_maps=expectancy_maps,
            )
            candidate.setup_score = round(self._compute_setup_score(candidate), 3)
            candidate.setup_status = self._determine_setup_status(candidate)
            candidate.structural_score = round(self._compute_structural_score(candidate), 3)

        candidates.sort(key=self._sort_key)
        self._candidates = candidates

    def list_candidates(self, limit: int | None = None) -> list[CandidateRecord]:
        if limit is None or limit <= 0:
            return list(self._candidates)
        return self._candidates[:limit]

    def _load_market_snapshot_rows(self) -> list[dict[str, str]]:
        if not self.market_snapshot_path.exists():
            raise FileNotFoundError(f"Market snapshot file not found: {self.market_snapshot_path}")
        with self.market_snapshot_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            return [dict(row) for row in reader]

    def _load_history_by_ticker(self) -> dict[str, list[DailySnapshotPoint]]:
        history: dict[str, list[DailySnapshotPoint]] = defaultdict(list)
        for path in sorted(self.snapshot_dir.glob("stock_snapshot_*.csv")):
            suffix = path.stem.replace("stock_snapshot_", "")
            try:
                file_date = date.fromisoformat(suffix)
            except ValueError:
                continue
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

    def _build_benchmark_history(
        self,
        history_by_ticker: dict[str, list[DailySnapshotPoint]],
    ) -> dict[str, dict[date, DailySnapshotPoint]]:
        benchmarks: dict[str, dict[date, DailySnapshotPoint]] = {}
        for ticker in {"SPY", "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"}:
            points = history_by_ticker.get(ticker, [])
            benchmarks[ticker] = {point.snapshot_date: point for point in points}
        return benchmarks

    def _build_benchmark_metric_cache(
        self,
        benchmark_history: dict[str, dict[date, DailySnapshotPoint]],
    ) -> dict[str, dict[date, dict[str, Any]]]:
        cache: dict[str, dict[date, dict[str, Any]]] = {}
        for ticker, points_by_date in benchmark_history.items():
            ordered = sorted(points_by_date.values(), key=lambda point: point.snapshot_date)
            cache[ticker] = {}
            for index in range(len(ordered)):
                metrics = self._build_historical_metrics(ticker, ordered[: index + 1])
                if metrics is None:
                    continue
                cache[ticker][ordered[index].snapshot_date] = {
                    "ticker": ticker,
                    "return_5d_pct": safe_round(metrics.return_5d_pct),
                    "return_20d_pct": safe_round(metrics.return_20d_pct),
                    "rsi14": safe_round(metrics.latest_rsi14),
                }
        return cache

    def _build_historical_metrics(
        self,
        ticker: str,
        points: list[DailySnapshotPoint],
    ) -> HistoricalMetrics | None:
        if not points:
            return None
        ordered = sorted(points, key=lambda point: point.snapshot_date)
        latest = ordered[-1]
        last_5 = ordered[-5:]
        last_20 = ordered[-20:]
        last_90 = ordered[-LOOKBACK_DAYS:]
        highs_90 = [point.day_high for point in last_90 if point.day_high is not None]
        resistance_90d = max(highs_90) if highs_90 else latest.high_20d
        touch_count_90d = None
        if resistance_90d not in (None, 0):
            tolerance = resistance_90d * 0.015
            touch_count_90d = sum(
                1
                for point in last_90
                if point.day_high is not None and point.day_high >= resistance_90d - tolerance
            )

        avg_volume_5d = (
            mean([point.day_volume for point in last_5 if point.day_volume is not None])
            if last_5
            else None
        )
        highs_50 = [point.day_high for point in ordered[-50:] if point.day_high is not None]
        lows_50 = [point.day_low for point in ordered[-50:] if point.day_low is not None]
        lows_90 = [point.day_low for point in last_90 if point.day_low is not None]
        support_20d = latest.low_20d
        if support_20d is None:
            support_20d = min([point.day_low for point in last_20 if point.day_low is not None], default=None)
        daily_ranges_14 = [
            point.day_high - point.day_low
            for point in ordered[-14:]
            if point.day_high is not None and point.day_low is not None
        ]
        daily_ranges_20 = [
            point.day_high - point.day_low
            for point in last_20
            if point.day_high is not None and point.day_low is not None
        ]

        range_position_day = None
        if latest.day_close is not None and latest.day_high is not None and latest.day_low is not None:
            day_range = latest.day_high - latest.day_low
            if day_range > 0:
                range_position_day = ((latest.day_close - latest.day_low) / day_range) * 100.0

        return HistoricalMetrics(
            ticker=ticker,
            latest_snapshot_date=latest.snapshot_date,
            latest_close=latest.day_close,
            latest_volume=latest.day_volume,
            latest_vwap=latest.vwap,
            latest_rsi14=latest.rsi14,
            avg_volume_5d=avg_volume_5d,
            resistance_20d=latest.high_20d
            if latest.high_20d is not None
            else max([point.day_high for point in last_20 if point.day_high is not None], default=None),
            support_20d=support_20d,
            resistance_50d=max(highs_50) if highs_50 else None,
            support_50d=min(lows_50) if lows_50 else None,
            resistance_90d=resistance_90d,
            support_90d=min(lows_90) if lows_90 else None,
            touch_count_90d=touch_count_90d,
            return_5d_pct=self._return_over_window(ordered, 5),
            return_20d_pct=self._return_over_window(ordered, 20),
            range_position_day_pct=range_position_day,
            avg_daily_range_14d=mean(daily_ranges_14) if daily_ranges_14 else None,
            avg_daily_range_20d=mean(daily_ranges_20) if daily_ranges_20 else None,
        )

    def _return_over_window(self, ordered: list[DailySnapshotPoint], window: int) -> float | None:
        if len(ordered) <= window:
            return None
        current = ordered[-1].day_close
        reference = ordered[-1 - window].day_close
        return pct_change(current, reference)

    def _build_candidate(
        self,
        *,
        snapshot_row: dict[str, str],
        history: list[DailySnapshotPoint],
        historical_metrics: HistoricalMetrics | None,
        benchmark_metric_cache: dict[str, dict[date, dict[str, Any]]],
        expectancy_maps: dict[str, dict[Any, dict[str, Any]]],
    ) -> CandidateRecord:
        symbol = (snapshot_row.get("ticker") or "").strip().upper()
        trade_date = parse_date(snapshot_row.get("snapshot_date"))
        if trade_date is None:
            raise ValueError(f"Snapshot row for {symbol} is missing snapshot_date.")

        current_price = self._first_number(
            snapshot_row.get("trend_close"),
            snapshot_row.get("day_current_price"),
            snapshot_row.get("day_close"),
            None if historical_metrics is None else historical_metrics.latest_close,
        )
        avg_volume_5d = None if historical_metrics is None else historical_metrics.avg_volume_5d
        latest_volume = None if historical_metrics is None else historical_metrics.latest_volume
        relative_volume_ratio = None
        if latest_volume is not None and avg_volume_5d not in (None, 0):
            relative_volume_ratio = latest_volume / avg_volume_5d

        daily_rsi = self._first_number(
            snapshot_row.get("trend_rsi14"),
            snapshot_row.get("rsi14"),
            None if historical_metrics is None else historical_metrics.latest_rsi14,
        )

        pattern_context = build_pattern_context(
            ticker_history=history,
            historical_metrics=historical_metrics,
            current_price=current_price,
            daily_rsi=daily_rsi,
            relative_volume_ratio=relative_volume_ratio,
        )
        validator_context = self._build_validator_context(
            snapshot_row=snapshot_row,
            history=history,
            historical_metrics=historical_metrics,
            benchmark_metric_cache=benchmark_metric_cache,
        )
        expectancy_context = self._select_expectancy_context(
            pattern_family=pattern_context.get("family"),
            category=(snapshot_row.get("selected_category") or "").strip() or None,
            validator_profile=validator_context.get("validator_profile"),
            expectancy_maps=expectancy_maps,
        )
        trade_plan_context = self._build_trade_plan_context(
            current_price=current_price,
            historical_metrics=historical_metrics,
            pattern_context=pattern_context,
            validator_context=validator_context,
            category=(snapshot_row.get("selected_category") or "").strip() or None,
        )

        return CandidateRecord(
            symbol=symbol,
            trade_date=trade_date,
            company_name=self._pick_company_name(snapshot_row, history),
            industry=self._pick_industry(snapshot_row, history),
            selected_category=(snapshot_row.get("selected_category") or "").strip() or None,
            trading_action=(snapshot_row.get("trading_action") or "").strip() or None,
            gnn_prob=parse_float(snapshot_row.get("gnn_prob")),
            trend_score=parse_float(snapshot_row.get("trend_score")),
            risk_bucket=(snapshot_row.get("risk_bucket") or "").strip().upper() or None,
            current_price=current_price,
            resistance_20d={
                "value": None if historical_metrics is None else historical_metrics.resistance_20d,
                "distance_pct": pct_change(
                    current_price,
                    None if historical_metrics is None else historical_metrics.resistance_20d,
                ),
            },
            relative_volume_context={
                "current_volume": latest_volume,
                "avg_volume_5d": avg_volume_5d,
                "ratio": safe_round(relative_volume_ratio),
            },
            daily_rsi_context={"value": daily_rsi},
            benchmark_context=validator_context.get("benchmark_context", {}),
            pattern_context=pattern_context,
            validator_context=validator_context,
            expectancy_context=expectancy_context,
            trade_plan_context=trade_plan_context,
            setup_score=0.0,
            setup_status="NOT_READY",
            structural_score=0.0,
            historical_metrics={} if historical_metrics is None else historical_metrics.to_dict(),
            raw_snapshot=snapshot_row,
        )

    def _build_validator_context(
        self,
        *,
        snapshot_row: dict[str, str],
        history: list[DailySnapshotPoint],
        historical_metrics: HistoricalMetrics | None,
        benchmark_metric_cache: dict[str, dict[date, dict[str, Any]]],
    ) -> dict[str, Any]:
        latest_point = history[-1] if history else None
        industry = self._pick_industry(snapshot_row, history)
        sector_etf = self._sector_etf_for_industry(industry)
        benchmark_date = latest_point.snapshot_date if latest_point is not None else None
        spy_metrics = self._benchmark_metrics("SPY", benchmark_date, benchmark_metric_cache)
        sector_metrics = (
            self._benchmark_metrics(sector_etf, benchmark_date, benchmark_metric_cache)
            if sector_etf
            else None
        )

        breakout_pass = False
        breakout_reason = "No usable daily breakout proxy was available."
        if historical_metrics is not None:
            close_value = historical_metrics.latest_close
            resistance = historical_metrics.resistance_20d
            range_pos = historical_metrics.range_position_day_pct
            breakout_pass = bool(
                close_value is not None
                and resistance is not None
                and close_value > resistance
                and range_pos is not None
                and range_pos >= 75
            )
            breakout_reason = (
                "Prior-day close finished above the 20-day resistance and in the top quartile of the daily range."
                if breakout_pass
                else "Prior-day close did not clear the resistance proxy with enough end-of-day conviction."
            )

        above_vwap_pass = False
        above_vwap_reason = "VWAP was unavailable in the prior-day history."
        if historical_metrics is not None:
            close_value = historical_metrics.latest_close
            vwap_value = historical_metrics.latest_vwap
            above_vwap_pass = bool(
                close_value is not None and vwap_value is not None and close_value > vwap_value
            )
            above_vwap_reason = (
                "Prior-day close finished above the daily VWAP."
                if above_vwap_pass
                else "Prior-day close finished at or below the daily VWAP."
            )

        relative_volume_ratio = None
        relative_volume_pass = False
        relative_volume_reason = "Relative volume could not be computed from the trailing 5-day history."
        if historical_metrics is not None:
            latest_volume = historical_metrics.latest_volume
            avg_volume_5d = historical_metrics.avg_volume_5d
            if latest_volume is not None and avg_volume_5d not in (None, 0):
                relative_volume_ratio = latest_volume / avg_volume_5d
                relative_volume_pass = relative_volume_ratio >= 1.0
                relative_volume_reason = (
                    "Prior-day volume expanded above the trailing 5-day average."
                    if relative_volume_pass
                    else "Participation lagged the trailing 5-day average volume."
                )

        stock_ret_5d = None if historical_metrics is None else historical_metrics.return_5d_pct
        stock_ret_20d = None if historical_metrics is None else historical_metrics.return_20d_pct
        stock_rsi = None if historical_metrics is None else historical_metrics.latest_rsi14

        relative_strength_price_pass, price_reason = self._relative_strength_price_check(
            stock_ret_5d=stock_ret_5d,
            stock_ret_20d=stock_ret_20d,
            spy_metrics=spy_metrics,
            sector_metrics=sector_metrics,
        )
        relative_strength_rsi_pass, rsi_reason = self._relative_strength_rsi_check(
            stock_rsi=stock_rsi,
            spy_metrics=spy_metrics,
            sector_metrics=sector_metrics,
        )

        checks = {
            "breakout_proxy": self._make_check("breakout_proxy", breakout_pass, breakout_reason, None),
            "above_vwap": self._make_check(
                "above_vwap",
                above_vwap_pass,
                above_vwap_reason,
                None if historical_metrics is None else historical_metrics.latest_vwap,
            ),
            "relative_volume": self._make_check(
                "relative_volume",
                relative_volume_pass,
                relative_volume_reason,
                safe_round(relative_volume_ratio),
            ),
            "relative_strength_price": self._make_check(
                "relative_strength_price",
                relative_strength_price_pass,
                price_reason,
                safe_round(stock_ret_5d),
            ),
            "relative_strength_rsi": self._make_check(
                "relative_strength_rsi",
                relative_strength_rsi_pass,
                rsi_reason,
                safe_round(stock_rsi),
            ),
        }

        aggregate_score = 0.0
        for name, check in checks.items():
            if check["passed"]:
                aggregate_score += VALIDATOR_WEIGHTS[name]

        rs_pair_pass = relative_strength_price_pass and relative_strength_rsi_pass
        if all(check["passed"] for check in checks.values()):
            validator_profile = "FULL_VALIDATION"
        elif breakout_pass and above_vwap_pass and (relative_strength_price_pass or relative_strength_rsi_pass) and not relative_volume_pass:
            validator_profile = "VOLUME_LAG"
        elif breakout_pass and above_vwap_pass and (relative_strength_price_pass or relative_strength_rsi_pass):
            validator_profile = "BREAKOUT_RS"
        elif sum(1 for check in checks.values() if check["passed"]) >= 3:
            validator_profile = "EARLY_SETUP"
        else:
            validator_profile = "FAILED"

        aggregate_status = (
            "PASS"
            if validator_profile in {"FULL_VALIDATION", "BREAKOUT_RS"}
            else "WATCH"
            if validator_profile in {"VOLUME_LAG", "EARLY_SETUP"}
            else "FAIL"
        )

        return {
            "checks": checks,
            "aggregate_score": round(aggregate_score, 2),
            "aggregate_status": aggregate_status,
            "validator_profile": validator_profile,
            "benchmark_context": {
                "spy": spy_metrics,
                "sector": sector_metrics,
                "sector_etf": sector_etf,
                "sector_mode": "SPY_AND_SECTOR" if sector_metrics is not None else "SPY_ONLY",
            },
        }

    def _relative_strength_price_check(
        self,
        *,
        stock_ret_5d: float | None,
        stock_ret_20d: float | None,
        spy_metrics: dict[str, Any] | None,
        sector_metrics: dict[str, Any] | None,
    ) -> tuple[bool, str]:
        if stock_ret_5d is None or stock_ret_20d is None or spy_metrics is None:
            return False, "Relative-strength price comparison was unavailable."
        spy_pass = (
            spy_metrics.get("return_5d_pct") is not None
            and spy_metrics.get("return_20d_pct") is not None
            and stock_ret_5d > spy_metrics["return_5d_pct"]
            and stock_ret_20d > spy_metrics["return_20d_pct"]
        )
        if not spy_pass:
            return False, "The stock underperformed SPY on the 5-day or 20-day return window."
        if sector_metrics is None:
            return True, "The stock outperformed SPY on both return windows; sector ETF fallback was unavailable."
        sector_pass = (
            sector_metrics.get("return_5d_pct") is not None
            and sector_metrics.get("return_20d_pct") is not None
            and stock_ret_5d > sector_metrics["return_5d_pct"]
            and stock_ret_20d > sector_metrics["return_20d_pct"]
        )
        if sector_pass:
            return True, "The stock outperformed both SPY and its sector ETF across the 5-day and 20-day windows."
        return False, "The stock outperformed SPY but not its sector ETF across both return windows."

    def _relative_strength_rsi_check(
        self,
        *,
        stock_rsi: float | None,
        spy_metrics: dict[str, Any] | None,
        sector_metrics: dict[str, Any] | None,
    ) -> tuple[bool, str]:
        if stock_rsi is None or spy_metrics is None or spy_metrics.get("rsi14") is None:
            return False, "Relative-strength RSI comparison was unavailable."
        if stock_rsi <= spy_metrics["rsi14"]:
            return False, "The stock RSI did not exceed SPY RSI."
        if sector_metrics is None or sector_metrics.get("rsi14") is None:
            return True, "The stock RSI exceeded SPY RSI; sector ETF fallback was unavailable."
        if stock_rsi > sector_metrics["rsi14"]:
            return True, "The stock RSI exceeded both SPY and sector ETF RSI."
        return False, "The stock RSI exceeded SPY RSI but not the sector ETF RSI."

    def _benchmark_metrics(
        self,
        ticker: str | None,
        benchmark_date: date | None,
        benchmark_metric_cache: dict[str, dict[date, dict[str, Any]]],
    ) -> dict[str, Any] | None:
        if not ticker or benchmark_date is None:
            return None
        metrics_by_date = benchmark_metric_cache.get(ticker)
        if not metrics_by_date:
            return None
        return metrics_by_date.get(benchmark_date)

    def _sector_etf_for_industry(self, industry: str | None) -> str | None:
        if not industry:
            return None
        lowered = industry.lower()
        for etf, keywords in SECTOR_ETF_RULES:
            if any(keyword in lowered for keyword in keywords):
                return etf
        return None

    def _build_expectancy_maps(
        self,
        row_by_ticker: dict[str, dict[str, str]],
        history_by_ticker: dict[str, list[DailySnapshotPoint]],
        benchmark_metric_cache: dict[str, dict[date, dict[str, Any]]],
    ) -> dict[str, dict[Any, dict[str, Any]]]:
        grouped_exact: dict[tuple[str, str | None, str], list[dict[str, Any]]] = defaultdict(list)
        grouped_family_category: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
        grouped_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
        grouped_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
        grouped_global: list[dict[str, Any]] = []

        for ticker, row in row_by_ticker.items():
            action = (row.get("trading_action") or "").strip().upper()
            if action in {"REDUCE", "EXIT"}:
                continue
            category = (row.get("selected_category") or "").strip() or None
            history = sorted(history_by_ticker.get(ticker, []), key=lambda point: point.snapshot_date)
            if len(history) < 25:
                continue
            for index in range(len(history)):
                if index < 19:
                    continue
                if index + max(EXPECTANCY_HORIZONS) >= len(history):
                    break
                lookback = history[: index + 1]
                metrics = self._build_historical_metrics(ticker, lookback)
                if metrics is None:
                    continue
                current_point = lookback[-1]
                current_price = current_point.day_close
                relative_volume_ratio = (
                    None
                    if metrics.latest_volume is None or metrics.avg_volume_5d in (None, 0)
                    else metrics.latest_volume / metrics.avg_volume_5d
                )
                pattern_context = build_pattern_context(
                    ticker_history=lookback,
                    historical_metrics=metrics,
                    current_price=current_price,
                    daily_rsi=metrics.latest_rsi14,
                    relative_volume_ratio=relative_volume_ratio,
                )
                validator_context = self._build_validator_context(
                    snapshot_row=row,
                    history=lookback,
                    historical_metrics=metrics,
                    benchmark_metric_cache=benchmark_metric_cache,
                )
                sample = self._build_outcome_sample(
                    ticker=ticker,
                    category=category,
                    pattern_family=pattern_context.get("family"),
                    validator_profile=validator_context.get("validator_profile"),
                    entry_price=current_price,
                    future_points=history[index + 1 : index + 1 + max(EXPECTANCY_HORIZONS)],
                )
                if sample is None:
                    continue
                grouped_exact[
                    (sample["pattern_family"], sample["category"], sample["validator_profile"])
                ].append(sample)
                grouped_family_category[(sample["pattern_family"], sample["category"])].append(sample)
                grouped_family[sample["pattern_family"]].append(sample)
                if sample["category"] is not None:
                    grouped_category[sample["category"]].append(sample)
                grouped_global.append(sample)

        return {
            "exact": {key: self._summarize_samples(samples) for key, samples in grouped_exact.items()},
            "family_category": {
                key: self._summarize_samples(samples) for key, samples in grouped_family_category.items()
            },
            "family": {key: self._summarize_samples(samples) for key, samples in grouped_family.items()},
            "category": {key: self._summarize_samples(samples) for key, samples in grouped_category.items()},
            "global": {"__all__": self._summarize_samples(grouped_global)},
        }

    def _build_outcome_sample(
        self,
        *,
        ticker: str,
        category: str | None,
        pattern_family: str | None,
        validator_profile: str | None,
        entry_price: float | None,
        future_points: list[DailySnapshotPoint],
    ) -> dict[str, Any] | None:
        if entry_price in (None, 0) or len(future_points) < max(EXPECTANCY_HORIZONS):
            return None
        sample = {
            "ticker": ticker,
            "category": category,
            "pattern_family": pattern_family or "Insufficient History",
            "validator_profile": validator_profile or "FAILED",
            "horizons": {},
        }
        for horizon in EXPECTANCY_HORIZONS:
            window = future_points[:horizon]
            end_close = window[-1].day_close
            highs = [point.day_high for point in window if point.day_high is not None]
            lows = [point.day_low for point in window if point.day_low is not None]
            if end_close is None or not highs or not lows:
                return None
            sample["horizons"][horizon] = {
                "end_return_pct": ((end_close / entry_price) - 1.0) * 100.0,
                "mfe_pct": ((max(highs) / entry_price) - 1.0) * 100.0,
                "mae_pct": ((min(lows) / entry_price) - 1.0) * 100.0,
            }
        return sample

    def _summarize_samples(self, samples: list[dict[str, Any]]) -> dict[str, Any]:
        if not samples:
            return {
                "sample_size": 0,
                "confidence": "LOW",
                "horizons": {},
            }
        summary = {
            "sample_size": len(samples),
            "confidence": "HIGH" if len(samples) >= 30 else "MEDIUM" if len(samples) >= 12 else "LOW",
            "horizons": {},
        }
        for horizon in EXPECTANCY_HORIZONS:
            outcomes = [sample["horizons"][horizon] for sample in samples]
            summary["horizons"][f"{horizon}d"] = {
                "win_rate": round(
                    sum(1 for outcome in outcomes if outcome["end_return_pct"] > 0) / len(outcomes),
                    3,
                ),
                "avg_end_return_pct": round(mean(outcome["end_return_pct"] for outcome in outcomes), 3),
                "avg_mfe_pct": round(mean(outcome["mfe_pct"] for outcome in outcomes), 3),
                "avg_mae_pct": round(mean(outcome["mae_pct"] for outcome in outcomes), 3),
            }
        return summary

    def _select_expectancy_context(
        self,
        *,
        pattern_family: str | None,
        category: str | None,
        validator_profile: str | None,
        expectancy_maps: dict[str, dict[Any, dict[str, Any]]],
    ) -> dict[str, Any]:
        options = [
            (
                "exact",
                (pattern_family or "Insufficient History", category, validator_profile or "FAILED"),
                "pattern_family+category+validator_profile",
            ),
            (
                "family_category",
                (pattern_family or "Insufficient History", category),
                "pattern_family+category",
            ),
            ("family", pattern_family or "Insufficient History", "pattern_family"),
            ("category", category, "category"),
            ("global", "__all__", "global"),
        ]

        chosen_level = "global"
        chosen_key: Any = "__all__"
        chosen_summary = expectancy_maps["global"].get(
            "__all__",
            {"sample_size": 0, "confidence": "LOW", "horizons": {}},
        )
        for level, key, label in options:
            if key is None:
                continue
            summary = expectancy_maps.get(level, {}).get(key)
            if summary and summary.get("sample_size", 0) >= MIN_EXPECTANCY_SAMPLES:
                chosen_level = label
                chosen_key = key
                chosen_summary = summary
                break

        return {
            "group_key": list(chosen_key) if isinstance(chosen_key, tuple) else chosen_key,
            "fallback_level": chosen_level,
            "sample_size": chosen_summary.get("sample_size", 0),
            "confidence": chosen_summary.get("confidence", "LOW"),
            "horizons": chosen_summary.get("horizons", {}),
        }

    def _build_trade_plan_context(
        self,
        *,
        current_price: float | None,
        historical_metrics: HistoricalMetrics | None,
        pattern_context: dict[str, Any],
        validator_context: dict[str, Any],
        category: str | None,
    ) -> dict[str, Any]:
        if historical_metrics is None or current_price in (None, 0):
            return {
                "entry_mode": "PULLBACK",
                "target_entry_price": None,
                "take_profit_price": None,
                "stop_loss_price": None,
                "risk_unit_price": None,
                "plan_reason": "Insufficient daily structure data for a price plan.",
            }

        profile = CATEGORY_RISK_PROFILES.get(
            (category or "").upper(),
            {"stop_buffer_mult": 0.8, "reward_multiple": 1.7},
        )
        volatility = self._volatility_proxy(historical_metrics)
        family = pattern_context.get("family")
        validator_status = validator_context.get("aggregate_status")
        breakout_families = {
            "Coiled Breakout",
            "High-Ground Leader",
            "Pressure Builder",
            "Momentum Expansion",
        }
        entry_mode = (
            "BREAKOUT"
            if family in breakout_families and validator_status in {"PASS", "WATCH"}
            else "PULLBACK"
        )
        if entry_mode == "BREAKOUT":
            return self._build_breakout_trade_plan(
                current_price=current_price,
                historical_metrics=historical_metrics,
                volatility=volatility,
                stop_buffer_mult=profile["stop_buffer_mult"],
                reward_multiple=profile["reward_multiple"],
            )
        return self._build_pullback_trade_plan(
            current_price=current_price,
            historical_metrics=historical_metrics,
            volatility=volatility,
            stop_buffer_mult=profile["stop_buffer_mult"],
            reward_multiple=profile["reward_multiple"],
        )

    def _volatility_proxy(self, historical_metrics: HistoricalMetrics) -> float:
        volatility = historical_metrics.avg_daily_range_14d
        if volatility in (None, 0):
            volatility = historical_metrics.avg_daily_range_20d
        if volatility in (None, 0):
            range_20 = None
            if historical_metrics.resistance_20d is not None and historical_metrics.support_20d is not None:
                range_20 = historical_metrics.resistance_20d - historical_metrics.support_20d
            volatility = range_20 / 10.0 if range_20 not in (None, 0) else 0.01
        return max(volatility, 0.01)

    def _build_breakout_trade_plan(
        self,
        *,
        current_price: float,
        historical_metrics: HistoricalMetrics,
        volatility: float,
        stop_buffer_mult: float,
        reward_multiple: float,
    ) -> dict[str, Any]:
        buffer = volatility * 0.15
        candidate_levels = [
            historical_metrics.resistance_20d,
            historical_metrics.resistance_50d,
            historical_metrics.resistance_90d,
        ]
        breakout_anchor = None
        for level in candidate_levels:
            if level is not None and level >= current_price:
                breakout_anchor = level
                break
        if breakout_anchor is None:
            breakout_anchor = next((level for level in candidate_levels if level is not None), current_price)

        target_entry = max(current_price, breakout_anchor) + buffer
        structure_reference = next(
            (
                level
                for level in (
                    historical_metrics.resistance_20d,
                    historical_metrics.resistance_50d,
                    historical_metrics.support_20d,
                )
                if level is not None
            ),
            current_price,
        )
        stop_loss = structure_reference - (volatility * stop_buffer_mult)
        stop_loss = min(stop_loss, target_entry - (volatility * 0.35))
        risk_unit = max(target_entry - stop_loss, volatility * 0.35)
        take_profit = target_entry + (risk_unit * reward_multiple)
        stop_loss, target_entry, take_profit = self._clamp_long_prices(stop_loss, target_entry, take_profit, volatility)
        return {
            "entry_mode": "BREAKOUT",
            "target_entry_price": safe_round(target_entry),
            "take_profit_price": safe_round(take_profit),
            "stop_loss_price": safe_round(stop_loss),
            "risk_unit_price": safe_round(target_entry - stop_loss),
            "plan_reason": "Breakout mode uses the nearest prior resistance with a volatility buffer and a stop below structural invalidation.",
        }

    def _build_pullback_trade_plan(
        self,
        *,
        current_price: float,
        historical_metrics: HistoricalMetrics,
        volatility: float,
        stop_buffer_mult: float,
        reward_multiple: float,
    ) -> dict[str, Any]:
        range_20 = None
        if historical_metrics.resistance_20d is not None and historical_metrics.support_20d is not None:
            range_20 = historical_metrics.resistance_20d - historical_metrics.support_20d
        range_50 = None
        if historical_metrics.resistance_50d is not None and historical_metrics.support_50d is not None:
            range_50 = historical_metrics.resistance_50d - historical_metrics.support_50d

        zone_candidates = []
        if range_20 not in (None, 0):
            zone_candidates.append(historical_metrics.support_20d + (range_20 * 0.62))
        if range_50 not in (None, 0):
            zone_candidates.append(historical_metrics.support_50d + (range_50 * 0.60))
        pullback_anchor = max(zone_candidates) if zone_candidates else current_price - (volatility * 0.3)
        target_entry = min(current_price, pullback_anchor)
        support_anchor = next(
            (
                level
                for level in (
                    historical_metrics.support_20d,
                    historical_metrics.support_50d,
                    historical_metrics.support_90d,
                )
                if level is not None
            ),
            current_price - volatility,
        )
        stop_loss = support_anchor - (volatility * stop_buffer_mult)
        stop_loss = min(stop_loss, target_entry - (volatility * 0.35))
        risk_unit = max(target_entry - stop_loss, volatility * 0.35)
        take_profit = target_entry + (risk_unit * reward_multiple)
        stop_loss, target_entry, take_profit = self._clamp_long_prices(stop_loss, target_entry, take_profit, volatility)
        return {
            "entry_mode": "PULLBACK",
            "target_entry_price": safe_round(target_entry),
            "take_profit_price": safe_round(take_profit),
            "stop_loss_price": safe_round(stop_loss),
            "risk_unit_price": safe_round(target_entry - stop_loss),
            "plan_reason": "Pullback mode uses an upper-half support zone from the recent structure with a stop below support plus a volatility buffer.",
        }

    def _clamp_long_prices(
        self,
        stop_loss: float,
        target_entry: float,
        take_profit: float,
        volatility: float,
    ) -> tuple[float, float, float]:
        min_gap = max(volatility * 0.1, 0.01)
        if stop_loss >= target_entry:
            stop_loss = target_entry - min_gap
        if take_profit <= target_entry:
            take_profit = target_entry + min_gap
        return stop_loss, target_entry, take_profit

    def _compute_structural_score(self, candidate: CandidateRecord) -> float:
        gnn_component = (candidate.gnn_prob or 0.0) * 35.0
        trend_component = (candidate.trend_score or 0.0) * 10.0
        action_component = ACTION_SCORES.get((candidate.trading_action or "").upper(), 0.0) * 8.0
        pattern_component = ((candidate.pattern_context.get("score") or 0.0) / 100.0) * 22.0
        validator_component = ((candidate.validator_context.get("aggregate_score") or 0.0) / 100.0) * 18.0
        return gnn_component + trend_component + action_component + pattern_component + validator_component

    def _compute_setup_score(self, candidate: CandidateRecord) -> float:
        structural_score = self._compute_structural_score(candidate)
        expectancy_5d = (
            candidate.expectancy_context.get("horizons", {})
            .get("5d", {})
            .get("avg_end_return_pct")
        )
        expectancy_component = 0.0
        if expectancy_5d is not None:
            clipped = max(-2.0, min(expectancy_5d, 6.0))
            expectancy_component = ((clipped + 2.0) / 8.0) * 12.0
        return structural_score + expectancy_component

    def _determine_setup_status(self, candidate: CandidateRecord) -> str:
        action = (candidate.trading_action or "").upper()
        validator_status = candidate.validator_context.get("aggregate_status")
        if action in {"REDUCE", "EXIT"}:
            return "NOT_READY"
        if candidate.setup_score >= 78 and validator_status == "PASS":
            return "HIGH_PRIORITY_SETUP"
        if candidate.setup_score >= 62 and validator_status in {"PASS", "WATCH"}:
            return "WATCHLIST"
        if candidate.setup_score >= 48:
            return "NEEDS_REVIEW"
        return "NOT_READY"

    def _sort_key(self, candidate: CandidateRecord) -> tuple[Any, ...]:
        status_rank = SETUP_STATUS_ORDER.get(candidate.setup_status, 9)
        validator_rank = VALIDATOR_STATUS_ORDER.get(
            candidate.validator_context.get("aggregate_status", "FAIL"),
            9,
        )
        expectancy_5d = candidate.expectancy_context.get("horizons", {}).get("5d", {}).get("avg_end_return_pct")
        return (
            status_rank,
            -candidate.setup_score,
            validator_rank,
            -(expectancy_5d or -999.0),
            -(candidate.gnn_prob or 0.0),
            candidate.symbol,
        )

    def _first_number(self, *values: Any) -> float | None:
        for value in values:
            parsed = parse_float(value)
            if parsed is not None:
                return parsed
        return None

    def _pick_company_name(self, snapshot_row: dict[str, str], history: list[DailySnapshotPoint]) -> str | None:
        value = (snapshot_row.get("ref_name") or "").strip()
        if value:
            return value
        if history and history[-1].ref_name:
            return history[-1].ref_name
        return None

    def _pick_industry(self, snapshot_row: dict[str, str], history: list[DailySnapshotPoint]) -> str | None:
        value = (snapshot_row.get("ref_industry") or "").strip()
        if value:
            return value
        if history and history[-1].ref_industry:
            return history[-1].ref_industry
        return None

    def _make_check(self, name: str, passed: bool, reason: str, value: Any) -> dict[str, Any]:
        return {
            "name": name,
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
            "reason": reason,
            "value": value,
        }

