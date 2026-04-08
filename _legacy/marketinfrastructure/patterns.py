from __future__ import annotations

from statistics import mean
from typing import Any

from .models import CandidateRecord, DailySnapshotPoint, HistoricalMetrics


LOOKBACK_DAYS = 90


def build_pattern_context(
    *,
    ticker_history: list[DailySnapshotPoint],
    historical_metrics: HistoricalMetrics | None,
    current_price: float | None,
    daily_rsi: float | None,
    relative_volume_ratio: float | None,
    blue_sky_context: dict[str, Any],
) -> dict[str, Any]:
    usable = sorted(ticker_history, key=lambda point: point.snapshot_date)[-LOOKBACK_DAYS:]
    if not usable or historical_metrics is None:
        return {
            "family": "Insufficient History",
            "score": None,
            "confidence": "LOW",
            "summary": "The 90-day pattern engine needs more local daily history before it can classify this setup.",
            "repeating_pattern_detected": False,
            "family_population": None,
            "similar_setups_today": [],
            "feature_signature": {},
        }

    highs_90 = [point.day_high for point in usable if point.day_high is not None]
    lows_90 = [point.day_low for point in usable if point.day_low is not None]
    closes_20 = [point.day_close for point in usable[-20:] if point.day_close is not None]
    highs_20 = [point.day_high for point in usable[-20:] if point.day_high is not None]
    lows_20 = [point.day_low for point in usable[-20:] if point.day_low is not None]
    volumes_20 = [point.day_volume for point in usable[-20:] if point.day_volume is not None]
    rsi_10 = [point.rsi14 for point in usable[-10:] if point.rsi14 is not None]

    high_90 = max(highs_90) if highs_90 else None
    low_90 = min(lows_90) if lows_90 else None
    high_20 = max(highs_20) if highs_20 else None
    low_20 = min(lows_20) if lows_20 else None

    range_90 = None if high_90 in (None, 0) or low_90 is None else high_90 - low_90
    range_20 = None if high_20 in (None, 0) or low_20 is None else high_20 - low_20
    compression_ratio = (
        None if range_20 in (None, 0) or range_90 in (None, 0) else range_20 / range_90
    )

    range_position_90 = None
    if current_price not in (None, 0) and range_90 not in (None, 0) and low_90 is not None:
        range_position_90 = ((current_price - low_90) / range_90) * 100.0

    close_to_90_high_pct = None
    if current_price not in (None, 0) and high_90 not in (None, 0):
        close_to_90_high_pct = ((current_price / high_90) - 1.0) * 100.0

    avg_volume_20 = mean(volumes_20) if volumes_20 else None
    latest_volume = historical_metrics.latest_volume
    volume_ratio_20 = (
        None if latest_volume in (None, 0) or avg_volume_20 in (None, 0) else latest_volume / avg_volume_20
    )
    if volume_ratio_20 is None:
        volume_ratio_20 = relative_volume_ratio

    avg_rsi_10 = mean(rsi_10) if rsi_10 else None
    rsi_trend = (
        None if daily_rsi is None or avg_rsi_10 is None else daily_rsi - avg_rsi_10
    )

    touch_count = historical_metrics.touch_count_90d or 0
    blue_sky_pass = (blue_sky_context.get("status") or "").upper() == "PASS"

    family = "Range Repair"
    summary = "The setup is still rebuilding structure inside its 90-day range."
    repeating_pattern_detected = False

    if (
        touch_count >= 3
        and compression_ratio is not None
        and compression_ratio <= 0.45
        and range_position_90 is not None
        and range_position_90 >= 70
    ):
        family = "Coiled Breakout"
        summary = "Repeated tests near resistance plus a compressed 90-day range suggest a coiled breakout pattern."
        repeating_pattern_detected = True
    elif blue_sky_pass and range_position_90 is not None and range_position_90 >= 82:
        family = "High-Ground Leader"
        summary = "The stock is holding the upper end of its 90-day range with limited overhead supply."
        repeating_pattern_detected = True
    elif (
        touch_count >= 2
        and range_position_90 is not None
        and range_position_90 >= 60
        and (rsi_trend or 0.0) >= 0
    ):
        family = "Pressure Builder"
        summary = "The chart is pressing into resistance with improving momentum and repeat interaction at the level."
        repeating_pattern_detected = True
    elif (volume_ratio_20 or 0.0) >= 1.1 and (daily_rsi or 0.0) >= 60:
        family = "Momentum Expansion"
        summary = "Participation and momentum are expanding inside the 90-day structure."
        repeating_pattern_detected = True

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
        "repeating_pattern_detected": repeating_pattern_detected,
        "family_population": None,
        "similar_setups_today": [],
        "feature_signature": {
            "touch_count_90d": touch_count,
            "compression_ratio": round(compression_ratio, 3) if compression_ratio is not None else None,
            "range_position_90d_pct": round(range_position_90, 2) if range_position_90 is not None else None,
            "close_to_90d_high_pct": round(close_to_90_high_pct, 2) if close_to_90_high_pct is not None else None,
            "volume_ratio_20d": round(volume_ratio_20, 2) if volume_ratio_20 is not None else None,
            "rsi_trend_10d": round(rsi_trend, 2) if rsi_trend is not None else None,
            "avg_volume_20d": round(avg_volume_20, 2) if avg_volume_20 is not None else None,
            "days_in_window": len(usable),
        },
    }


def attach_pattern_peers(candidates: list[CandidateRecord]) -> None:
    grouped: dict[str, list[CandidateRecord]] = {}
    for candidate in candidates:
        family = candidate.pattern_context.get("family", "Unknown")
        grouped.setdefault(family, []).append(candidate)

    for family, members in grouped.items():
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
