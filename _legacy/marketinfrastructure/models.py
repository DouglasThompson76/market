from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any


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
    resistance_90d: float | None
    touch_count_90d: int | None
    prior_range_high: float | None
    prior_range_low: float | None
    prior_range_width: float | None
    prior_range_position_pct: float | None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.latest_snapshot_date is not None:
            payload["latest_snapshot_date"] = self.latest_snapshot_date.isoformat()
        return payload


@dataclass(slots=True)
class GoldenHourSignal:
    symbol: str
    trade_date: date
    opening_range_high: float
    trigger_time_et: str
    trigger_bar_close: float
    trigger_bar_volume: float
    opening_range_avg_bar_volume: float
    session_vwap_at_trigger: float
    relative_strength_vs_spy: float
    passed_time_cutoff: bool
    passed_orb_close: bool
    passed_volume_confirmation: bool
    passed_vwap_filter: bool

    @property
    def passed_all(self) -> bool:
        return (
            self.passed_time_cutoff
            and self.passed_orb_close
            and self.passed_volume_confirmation
            and self.passed_vwap_filter
        )

    def status(self) -> str:
        return (
            "EXTERNAL_CONFIRMATION_READY"
            if self.passed_all
            else "EXTERNAL_CONFIRMATION_REJECTED"
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["trade_date"] = self.trade_date.isoformat()
        payload["passed_all"] = self.passed_all
        payload["status"] = self.status()
        return payload


@dataclass(slots=True)
class CandidateRecord:
    symbol: str
    trade_date: date
    company_name: str | None
    industry: str | None
    gnn_prob: float | None
    selected_category: str | None
    trading_action: str | None
    management_action: str | None
    risk_bucket: str | None
    setup_priority: str
    setup_status: str
    current_price_context: dict[str, Any]
    resistance_20d: dict[str, Any]
    relative_volume_context: dict[str, Any]
    daily_rsi_context: dict[str, Any]
    vwap_context: dict[str, Any]
    pink_line_context: dict[str, Any]
    squeeze_context: dict[str, Any]
    blue_sky_context: dict[str, Any]
    narrative_context: dict[str, Any]
    pattern_context: dict[str, Any]
    newssentiment: str | None
    newscore: float | None
    top_influencer: str | None
    top_influence_type: str | None
    favor_checks_local: dict[str, dict[str, Any]]
    manual_open_checklist: list[str]
    handoff_message: str
    requires_intraday_confirmation: bool
    alert_message: str
    structural_score: float
    setup_score: float
    raw_snapshot: dict[str, Any]
    historical_metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["trade_date"] = self.trade_date.isoformat()
        return payload
