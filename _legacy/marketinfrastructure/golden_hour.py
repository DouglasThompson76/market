from __future__ import annotations

import json
from datetime import date
from typing import Any

from .models import GoldenHourSignal


REQUIRED_FIELDS = (
    "symbol",
    "trade_date",
    "opening_range_high",
    "trigger_time_et",
    "trigger_bar_close",
    "trigger_bar_volume",
    "opening_range_avg_bar_volume",
    "session_vwap_at_trigger",
    "relative_strength_vs_spy",
    "passed_time_cutoff",
    "passed_orb_close",
    "passed_volume_confirmation",
    "passed_vwap_filter",
)


class GoldenHourValidationError(ValueError):
    """Raised when an external golden-hour payload is malformed."""


def sample_payload() -> list[dict[str, Any]]:
    return [
        {
            "symbol": "NVDA",
            "trade_date": "2026-03-25",
            "opening_range_high": 917.42,
            "trigger_time_et": "10:17:00",
            "trigger_bar_close": 919.05,
            "trigger_bar_volume": 1724330,
            "opening_range_avg_bar_volume": 998210,
            "session_vwap_at_trigger": 915.66,
            "relative_strength_vs_spy": 1.42,
            "passed_time_cutoff": True,
            "passed_orb_close": True,
            "passed_volume_confirmation": True,
            "passed_vwap_filter": True,
        }
    ]


def parse_payload_bytes(payload: bytes) -> list[GoldenHourSignal]:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GoldenHourValidationError(f"Invalid JSON payload: {exc}") from exc
    return parse_payload_object(raw)


def parse_payload_object(raw: Any) -> list[GoldenHourSignal]:
    if isinstance(raw, dict):
        if "signals" not in raw:
            raise GoldenHourValidationError(
                "JSON object payloads must contain a top-level 'signals' array."
            )
        raw = raw["signals"]
    if not isinstance(raw, list):
        raise GoldenHourValidationError("Golden-hour payload must be a JSON array.")
    signals = [parse_signal_object(item) for item in raw]
    seen = set()
    for signal in signals:
        key = (signal.symbol, signal.trade_date.isoformat())
        if key in seen:
            raise GoldenHourValidationError(
                f"Duplicate golden-hour entry found for {signal.symbol} on {signal.trade_date.isoformat()}."
            )
        seen.add(key)
    return signals


def parse_signal_object(raw: Any) -> GoldenHourSignal:
    if not isinstance(raw, dict):
        raise GoldenHourValidationError("Each golden-hour entry must be a JSON object.")
    missing = [field for field in REQUIRED_FIELDS if field not in raw]
    if missing:
        raise GoldenHourValidationError(
            "Golden-hour entry is missing required fields: " + ", ".join(missing)
        )
    symbol = str(raw["symbol"]).strip().upper()
    if not symbol:
        raise GoldenHourValidationError("Golden-hour entry has an empty symbol.")
    try:
        trade_date = date.fromisoformat(str(raw["trade_date"]))
    except ValueError as exc:
        raise GoldenHourValidationError(
            f"Invalid trade_date for {symbol}: {raw['trade_date']!r}"
        ) from exc
    return GoldenHourSignal(
        symbol=symbol,
        trade_date=trade_date,
        opening_range_high=parse_float(raw["opening_range_high"], "opening_range_high"),
        trigger_time_et=str(raw["trigger_time_et"]).strip(),
        trigger_bar_close=parse_float(raw["trigger_bar_close"], "trigger_bar_close"),
        trigger_bar_volume=parse_float(raw["trigger_bar_volume"], "trigger_bar_volume"),
        opening_range_avg_bar_volume=parse_float(
            raw["opening_range_avg_bar_volume"], "opening_range_avg_bar_volume"
        ),
        session_vwap_at_trigger=parse_float(
            raw["session_vwap_at_trigger"], "session_vwap_at_trigger"
        ),
        relative_strength_vs_spy=parse_float(
            raw["relative_strength_vs_spy"], "relative_strength_vs_spy"
        ),
        passed_time_cutoff=parse_bool(raw["passed_time_cutoff"], "passed_time_cutoff"),
        passed_orb_close=parse_bool(raw["passed_orb_close"], "passed_orb_close"),
        passed_volume_confirmation=parse_bool(
            raw["passed_volume_confirmation"], "passed_volume_confirmation"
        ),
        passed_vwap_filter=parse_bool(raw["passed_vwap_filter"], "passed_vwap_filter"),
    )


def parse_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise GoldenHourValidationError(f"{field} must be numeric.") from exc


def parse_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise GoldenHourValidationError(f"{field} must be a boolean.")

