from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .data import MarketDataRepository, parse_date, parse_float
from .models import CandidateRecord, HistoricalMetrics
from .patterns import attach_pattern_peers, build_pattern_context


ACTION_SCORES = {
    "BUY": 1.0,
    "ADD": 0.9,
    "HOLD": 0.7,
    "WATCH_ONLY": 0.45,
    "REDUCE": 0.1,
    "EXIT": 0.0,
}

RISK_PENALTIES = {
    "LOW": 0.0,
    "MEDIUM": 0.05,
    "HIGH": 0.12,
    "VERY_HIGH": 0.2,
}

SETUP_STATUS_ORDER = {
    "HIGH_PRIORITY_SETUP": 0,
    "WATCHLIST": 1,
    "NEEDS_REVIEW": 2,
    "NOT_READY": 3,
}

RISK_BUCKET_ORDER = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "VERY_HIGH": 3,
}


class MarketInfrastructureService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.repository = MarketDataRepository(self.project_root)
        self._candidate_cache: list[CandidateRecord] = []
        self._candidate_index: dict[tuple[str, str], CandidateRecord] = {}
        self.refresh()

    def refresh(self) -> None:
        market_rows = self.repository.load_market_snapshot_rows()
        trade_dates = {
            parsed_date
            for row in market_rows
            if (parsed_date := parse_date(row.get("snapshot_date")))
        }
        history = self.repository.load_history_by_ticker(trade_dates)
        histories_by_trade_date = {
            trade_date: self.repository.build_historical_metrics(history, trade_date)
            for trade_date in trade_dates
        }

        candidates: list[CandidateRecord] = []
        for row in market_rows:
            trade_date = parse_date(row.get("snapshot_date"))
            if trade_date is None:
                continue
            ticker = (row.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            historical_metrics = histories_by_trade_date.get(trade_date, {}).get(ticker)
            candidates.append(
                self._build_candidate(
                    snapshot_row=row,
                    historical_metrics=historical_metrics,
                    ticker_history=history.get(ticker, []),
                )
            )

        attach_pattern_peers(candidates)
        candidates.sort(key=self._sort_key)
        self._candidate_cache = candidates
        self._candidate_index = {
            (candidate.symbol, candidate.trade_date.isoformat()): candidate
            for candidate in candidates
        }

    def describe(self) -> dict[str, Any]:
        status_counts = Counter(candidate.setup_status for candidate in self._candidate_cache)
        return {
            "project_root": str(self.project_root),
            "candidate_count": len(self._candidate_cache),
            "trade_dates": sorted(
                {candidate.trade_date.isoformat() for candidate in self._candidate_cache}
            ),
            "setup_status_counts": dict(status_counts),
            "top_symbols": [candidate.symbol for candidate in self._candidate_cache[:5]],
        }

    def list_candidates(
        self,
        *,
        search: str = "",
        category: str = "",
        action: str = "",
        risk_bucket: str = "",
        status: str = "",
        sort_by: str = "",
        sort_dir: str = "",
        limit: int = 100,
    ) -> list[CandidateRecord]:
        search = search.strip().upper()
        category = category.strip()
        action = action.strip().upper()
        risk_bucket = risk_bucket.strip().upper()
        status = status.strip().upper()
        sort_by = sort_by.strip().lower()
        sort_dir = sort_dir.strip().lower()

        results = []
        for candidate in self._candidate_cache:
            if search and search not in candidate.symbol and search not in (
                (candidate.company_name or "").upper()
            ):
                continue
            if category and candidate.selected_category != category:
                continue
            if action and (candidate.trading_action or "").upper() != action:
                continue
            if risk_bucket and (candidate.risk_bucket or "").upper() != risk_bucket:
                continue
            if status and candidate.setup_status.upper() != status:
                continue
            results.append(candidate)
        if sort_by:
            results.sort(key=lambda candidate: self._sortable_value(candidate, sort_by))
            if sort_dir == "desc":
                results.reverse()
        elif sort_dir == "desc":
            results = list(reversed(results))
        limited = []
        for candidate in results:
            limited.append(candidate)
            if len(limited) >= limit:
                break
        return limited

    def get_candidate(self, symbol: str, trade_date: str) -> CandidateRecord | None:
        return self._candidate_index.get((symbol.upper(), trade_date))

    def available_filters(self) -> dict[str, list[str]]:
        categories = sorted(
            {
                candidate.selected_category
                for candidate in self._candidate_cache
                if candidate.selected_category
            }
        )
        actions = sorted(
            {candidate.trading_action for candidate in self._candidate_cache if candidate.trading_action}
        )
        risk_buckets = sorted(
            {candidate.risk_bucket for candidate in self._candidate_cache if candidate.risk_bucket}
        )
        statuses = sorted(
            {candidate.setup_status for candidate in self._candidate_cache},
            key=lambda item: SETUP_STATUS_ORDER.get(item, 9),
        )
        return {
            "categories": categories,
            "actions": actions,
            "risk_buckets": risk_buckets,
            "statuses": statuses,
        }

    def _build_candidate(
        self,
        *,
        snapshot_row: dict[str, str],
        historical_metrics: HistoricalMetrics | None,
        ticker_history: list[Any],
    ) -> CandidateRecord:
        symbol = (snapshot_row.get("ticker") or "").strip().upper()
        trade_date = parse_date(snapshot_row.get("snapshot_date"))
        if trade_date is None:
            raise ValueError(f"Snapshot row for {symbol} is missing snapshot_date.")

        company_name = (snapshot_row.get("ref_name") or "").strip() or None
        industry = (snapshot_row.get("ref_industry") or "").strip() or None
        current_price = self._first_number(
            snapshot_row.get("trend_close"),
            None if historical_metrics is None else historical_metrics.latest_close,
            snapshot_row.get("day_close"),
        )
        current_price_source = self._first_source(
            ("trend_close", snapshot_row.get("trend_close")),
            (
                "snapshot_history.latest_close",
                None if historical_metrics is None else historical_metrics.latest_close,
            ),
            ("day_close", snapshot_row.get("day_close")),
        )

        resistance = self._first_number(
            snapshot_row.get("high_20d"),
            None if historical_metrics is None else historical_metrics.resistance_20d,
        )
        resistance_source = self._first_source(
            ("high_20d", snapshot_row.get("high_20d")),
            (
                "snapshot_history.resistance_20d",
                None if historical_metrics is None else historical_metrics.resistance_20d,
            ),
        )
        resistance_distance_pct = None
        if current_price not in (None, 0) and resistance not in (None, 0):
            resistance_distance_pct = ((current_price / resistance) - 1.0) * 100.0

        avg_volume_5d = None if historical_metrics is None else historical_metrics.avg_volume_5d
        current_volume = self._first_number(
            snapshot_row.get("trend_volume"),
            None if historical_metrics is None else historical_metrics.latest_volume,
            snapshot_row.get("day_volume"),
        )
        current_volume_source = self._first_source(
            ("trend_volume", snapshot_row.get("trend_volume")),
            (
                "snapshot_history.latest_volume",
                None if historical_metrics is None else historical_metrics.latest_volume,
            ),
            ("day_volume", snapshot_row.get("day_volume")),
        )
        relative_volume_ratio = None
        if current_volume is not None and avg_volume_5d not in (None, 0):
            relative_volume_ratio = current_volume / avg_volume_5d

        daily_rsi = self._first_number(
            snapshot_row.get("trend_rsi14"),
            None if historical_metrics is None else historical_metrics.latest_rsi14,
            snapshot_row.get("rsi14"),
        )
        daily_rsi_source = self._first_source(
            ("trend_rsi14", snapshot_row.get("trend_rsi14")),
            (
                "snapshot_history.latest_rsi14",
                None if historical_metrics is None else historical_metrics.latest_rsi14,
            ),
            ("rsi14", snapshot_row.get("rsi14")),
        )

        vwap_value = self._first_number(
            snapshot_row.get("trend_vwap_20d"),
            None if historical_metrics is None else historical_metrics.latest_vwap,
            snapshot_row.get("vwap"),
        )
        vwap_source = self._first_source(
            ("trend_vwap_20d", snapshot_row.get("trend_vwap_20d")),
            (
                "snapshot_history.latest_vwap",
                None if historical_metrics is None else historical_metrics.latest_vwap,
            ),
            ("vwap", snapshot_row.get("vwap")),
        )
        is_above_vwap = None if current_price is None or vwap_value is None else current_price > vwap_value

        newssentiment = (snapshot_row.get("newssentiment") or "").strip() or None
        newscore = parse_float(snapshot_row.get("newscore"))
        pink_line_context = self._build_pink_line_context(
            snapshot_row=snapshot_row,
            historical_metrics=historical_metrics,
            current_price=current_price,
            fallback_resistance=resistance,
            fallback_source=resistance_source,
        )
        squeeze_context = self._build_squeeze_context(
            snapshot_row=snapshot_row,
            historical_metrics=historical_metrics,
            current_price=current_price,
        )
        blue_sky_context = self._build_blue_sky_context(snapshot_row)
        narrative_context = self._build_narrative_context(
            snapshot_row=snapshot_row,
            newssentiment=newssentiment,
            newscore=newscore,
        )
        pattern_context = build_pattern_context(
            ticker_history=ticker_history,
            historical_metrics=historical_metrics,
            current_price=current_price,
            daily_rsi=daily_rsi,
            relative_volume_ratio=relative_volume_ratio,
            blue_sky_context=blue_sky_context,
        )

        gnn_prob = parse_float(snapshot_row.get("gnn_prob"))
        trend_score = parse_float(snapshot_row.get("trend_score")) or 0.0
        action_score = ACTION_SCORES.get((snapshot_row.get("trading_action") or "").upper(), 0.0)
        risk_bucket = (snapshot_row.get("risk_bucket") or "").upper() or None
        risk_penalty = RISK_PENALTIES.get(risk_bucket or "", 0.08)
        structural_score = (
            (gnn_prob or 0.0) * 40.0
            + trend_score * 18.0
            + action_score * 10.0
            + self._score_resistance_context(resistance_distance_pct)
            + self._score_relative_volume(relative_volume_ratio)
            + self._score_rsi(daily_rsi)
            + self._score_blue_sky(blue_sky_context)
            + self._score_squeeze(squeeze_context)
            - risk_penalty * 22.0
        )
        setup_score = (
            structural_score
            + self._score_narrative(narrative_context)
            + self._score_pattern(pattern_context)
        )

        favor_checks = {
            "gnn_support": self._make_check(
                label="GNN Support",
                status=self._threshold_status(gnn_prob, high=0.75, medium=0.6),
                value=gnn_prob,
                reason="Uses the embedded GNN confidence from MarketSnapshot_output.csv to rank structural quality before the open.",
            ),
            "pink_line_context": self._make_check(
                label="Pink Line",
                status=pink_line_context["status"],
                value=pink_line_context["distance_pct"],
                reason=pink_line_context["reason"],
            ),
            "squeeze_context": self._make_check(
                label="HTF Squeeze",
                status=squeeze_context["status"],
                value=squeeze_context["compression_score"],
                reason=squeeze_context["reason"],
            ),
            "blue_sky_context": self._make_check(
                label="Blue Sky",
                status=blue_sky_context["status"],
                value=blue_sky_context["distance_to_52w_high_pct"],
                reason=blue_sky_context["reason"],
            ),
            "narrative_context": self._make_check(
                label="Narrative",
                status=narrative_context["status"],
                value=narrative_context["score"],
                reason=narrative_context["reason"],
            ),
            "pattern_context": self._make_check(
                label="Pattern Intelligence",
                status=self._pattern_check_status(pattern_context),
                value=pattern_context["score"],
                reason=pattern_context["summary"],
            ),
            "relative_volume_context": self._make_check(
                label="Relative Volume",
                status=(
                    "PASS"
                    if relative_volume_ratio is not None and relative_volume_ratio >= 1.0
                    else "WATCH"
                    if relative_volume_ratio is not None and relative_volume_ratio >= 0.75
                    else "FAIL"
                ),
                value=relative_volume_ratio,
                reason="Uses 5-day average volume from the 90-day snapshot history to tell whether the setup already has participation behind it.",
            ),
            "risk_context": self._make_check(
                label="Risk Bucket",
                status="PASS" if risk_bucket in {"LOW", "MEDIUM"} else "WATCH" if risk_bucket == "HIGH" else "FAIL",
                value=risk_bucket,
                reason="Keeps the premarket board focused on structurally strong names without ignoring risk.",
            ),
        }

        setup_status = self._determine_setup_status(
            setup_score=setup_score,
            narrative_context=narrative_context,
            action=(snapshot_row.get("trading_action") or "").strip().upper(),
            risk_bucket=risk_bucket,
        )
        setup_priority = self._setup_priority(setup_status)
        handoff_message = (
            "Use the separate intraday system after the open to confirm the minute-by-minute trigger and execution timing."
        )
        manual_open_checklist = [
            "Confirm the opening move is interacting with the key resistance level from the 90-day setup.",
            "Wait for the separate intraday system to validate the exact opening-range breakout and live volume expansion.",
            "Check that price stays above intraday VWAP and does not immediately reject the level after the open.",
            "Verify the catalyst still matters in real time and that the move is not being faded by the market or sector.",
        ]

        return CandidateRecord(
            symbol=symbol,
            trade_date=trade_date,
            company_name=company_name,
            industry=industry,
            gnn_prob=gnn_prob,
            selected_category=(snapshot_row.get("selected_category") or "").strip() or None,
            trading_action=(snapshot_row.get("trading_action") or "").strip() or None,
            management_action=(snapshot_row.get("management_action") or "").strip() or None,
            risk_bucket=risk_bucket,
            setup_priority=setup_priority,
            setup_status=setup_status,
            current_price_context={"price": current_price, "source": current_price_source},
            resistance_20d={
                "value": resistance,
                "distance_pct": resistance_distance_pct,
                "source": resistance_source,
            },
            relative_volume_context={
                "current_volume": current_volume,
                "avg_volume_5d": avg_volume_5d,
                "ratio": relative_volume_ratio,
                "source": (
                    None
                    if current_volume_source is None
                    else f"{current_volume_source}_vs_snapshot_history_5d_avg"
                ),
            },
            daily_rsi_context={"value": daily_rsi, "source": daily_rsi_source},
            vwap_context={
                "value": vwap_value,
                "source": vwap_source,
                "is_above_vwap": is_above_vwap,
            },
            pink_line_context=pink_line_context,
            squeeze_context=squeeze_context,
            blue_sky_context=blue_sky_context,
            narrative_context=narrative_context,
            pattern_context=pattern_context,
            newssentiment=newssentiment,
            newscore=newscore,
            top_influencer=(snapshot_row.get("top_influencer") or "").strip() or None,
            top_influence_type=(snapshot_row.get("influence_type") or "").strip() or None,
            favor_checks_local=favor_checks,
            manual_open_checklist=manual_open_checklist,
            handoff_message=handoff_message,
            requires_intraday_confirmation=True,
            alert_message=self._make_alert_message(
                symbol=symbol,
                setup_status=setup_status,
                setup_priority=setup_priority,
                candidate_category=(snapshot_row.get("selected_category") or "").strip() or "Unclassified",
                action=(snapshot_row.get("trading_action") or "").strip() or "WATCH_ONLY",
                narrative_context=narrative_context,
            ),
            structural_score=round(structural_score, 3),
            setup_score=round(setup_score, 3),
            raw_snapshot=snapshot_row,
            historical_metrics={}
            if historical_metrics is None
            else historical_metrics.to_dict(),
        )

    def _sort_key(self, candidate: CandidateRecord) -> tuple[Any, ...]:
        status_rank = SETUP_STATUS_ORDER.get(candidate.setup_status, 9)
        return (
            status_rank,
            -candidate.setup_score,
            -(candidate.gnn_prob or 0.0),
            candidate.symbol,
        )

    def _sortable_value(self, candidate: CandidateRecord, sort_by: str) -> tuple[int, Any, str]:
        if sort_by == "symbol":
            value = candidate.symbol
        elif sort_by == "price":
            value = candidate.current_price_context.get("price")
        elif sort_by == "priority":
            value = int(candidate.setup_priority.split()[-1])
        elif sort_by == "setup":
            value = SETUP_STATUS_ORDER.get(candidate.setup_status, 9)
        elif sort_by == "gnn":
            value = candidate.gnn_prob
        elif sort_by == "news":
            value = candidate.newscore
        elif sort_by == "pattern":
            value = candidate.pattern_context.get("score")
        elif sort_by == "pink_line":
            value = candidate.pink_line_context.get("distance_pct")
        elif sort_by == "squeeze":
            value = candidate.squeeze_context.get("compression_score")
        elif sort_by == "blue_sky":
            value = candidate.blue_sky_context.get("distance_to_52w_high_pct")
        elif sort_by == "risk":
            value = RISK_BUCKET_ORDER.get((candidate.risk_bucket or "").upper())
        else:
            value = None
        return (value is None, value if value is not None else 0, candidate.symbol)

    def _build_pink_line_context(
        self,
        *,
        snapshot_row: dict[str, str],
        historical_metrics: HistoricalMetrics | None,
        current_price: float | None,
        fallback_resistance: float | None,
        fallback_source: str | None,
    ) -> dict[str, Any]:
        high_50d = self._first_number(snapshot_row.get("high_50d"))
        high_52w = self._first_number(snapshot_row.get("high_52w"))
        resistance_90d = (
            None if historical_metrics is None else historical_metrics.resistance_90d
        )
        touch_count_90d = (
            None if historical_metrics is None else historical_metrics.touch_count_90d
        )
        level = self._first_number(resistance_90d, fallback_resistance, high_50d, high_52w)
        source = self._first_source(
            ("snapshot_history.resistance_90d", resistance_90d),
            (fallback_source or "fallback_resistance", fallback_resistance),
            ("high_50d", snapshot_row.get("high_50d")),
            ("high_52w", snapshot_row.get("high_52w")),
        )
        distance_pct = None
        if current_price not in (None, 0) and level not in (None, 0):
            distance_pct = ((current_price / level) - 1.0) * 100.0

        compared_levels = [value for value in (fallback_resistance, high_50d, high_52w) if value is not None]
        fallback_cluster = False
        if len(compared_levels) >= 2 and max(compared_levels):
            fallback_cluster = ((max(compared_levels) - min(compared_levels)) / max(compared_levels)) <= 0.05
        repeated_resistance = (
            touch_count_90d >= 3 if touch_count_90d is not None else fallback_cluster
        )

        if level is None:
            status = "FAIL"
            reason = "No clear resistance level was found in the local 90-day structure."
        elif repeated_resistance and distance_pct is not None and distance_pct >= -5:
            status = "PASS"
            if touch_count_90d is not None:
                reason = (
                    f"The 90-day resistance has been tested {touch_count_90d} times and price is still close enough to that level for a valid pink-line setup."
                )
            else:
                reason = "The available resistance levels cluster tightly enough to act like a tested pink-line resistance."
        elif touch_count_90d is not None and touch_count_90d >= 2:
            status = "WATCH"
            reason = (
                f"The 90-day resistance has {touch_count_90d} nearby tests, but it needs one more clean touch or a tighter approach into the open."
            )
        elif repeated_resistance:
            status = "WATCH"
            reason = "A tested resistance level exists, but price is still too far below it for a clean premarket pink-line setup."
        elif touch_count_90d is not None:
            status = "FAIL"
            reason = "The 90-day history does not show enough repeated touches at resistance to qualify as a pink-line setup."
        else:
            status = "WATCH"
            reason = "A usable resistance level exists, but the repeated-test structure still needs human review."
        return {
            "level": level,
            "source": source,
            "distance_pct": distance_pct,
            "resistance_90d": resistance_90d,
            "touch_count_90d": touch_count_90d,
            "high_50d": high_50d,
            "high_52w": high_52w,
            "repeated_resistance": repeated_resistance,
            "status": status,
            "reason": reason,
        }

    def _build_squeeze_context(
        self,
        *,
        snapshot_row: dict[str, str],
        historical_metrics: HistoricalMetrics | None,
        current_price: float | None,
    ) -> dict[str, Any]:
        range_20d = self._first_number(snapshot_row.get("range_20d"))
        range_50d = self._first_number(snapshot_row.get("range_50d"))
        vol_20d = self._first_number(snapshot_row.get("trend_vol_20d"), snapshot_row.get("vol20"))
        vol_50d = self._first_number(snapshot_row.get("trend_vol_50d"), snapshot_row.get("vol50"))
        range_ratio = (
            None if range_20d in (None, 0) or range_50d in (None, 0) else range_20d / range_50d
        )
        vol_ratio = (
            None if vol_20d in (None, 0) or vol_50d in (None, 0) else vol_20d / vol_50d
        )
        compression_score = 0.0
        if range_ratio is not None:
            compression_score += max(0.0, 1.5 - range_ratio)
        if vol_ratio is not None:
            compression_score += max(0.0, 1.5 - vol_ratio)
        if historical_metrics and current_price not in (None, 0) and historical_metrics.prior_range_width:
            compression_score += max(
                0.0,
                1.0 - (historical_metrics.prior_range_width / current_price),
            )
        compression_score = round(compression_score, 3)
        if range_ratio is not None and vol_ratio is not None and range_ratio <= 0.75 and vol_ratio <= 0.9:
            status = "PASS"
            reason = "The daily range and volatility have tightened enough to suggest a higher-timeframe squeeze."
        elif range_ratio is not None or vol_ratio is not None:
            status = "WATCH"
            reason = "Compression is present, but the squeeze is not yet clean across both range and volatility."
        else:
            status = "WATCH"
            reason = "Compression data is incomplete, so the squeeze case needs human review."
        return {
            "range_ratio": range_ratio,
            "volatility_ratio": vol_ratio,
            "compression_score": compression_score,
            "status": status,
            "reason": reason,
        }

    def _build_blue_sky_context(self, snapshot_row: dict[str, str]) -> dict[str, Any]:
        distance_to_52w_high = self._first_number(snapshot_row.get("dist_from_52w_high_pct"))
        is_52w_high = self._truthy(snapshot_row.get("is_52w_high"))
        is_near_52w_high = self._truthy(snapshot_row.get("is_near_52w_high"))
        if is_52w_high or is_near_52w_high or (
            distance_to_52w_high is not None and distance_to_52w_high >= -5.0
        ):
            status = "PASS"
            reason = "The name is trading close enough to its 52-week high that overhead resistance looks limited."
        elif distance_to_52w_high is not None and distance_to_52w_high >= -10.0:
            status = "WATCH"
            reason = "The name is reasonably close to blue-sky territory, but some overhead supply may remain."
        else:
            status = "FAIL"
            reason = "The 52-week structure suggests too much overhead resistance for a clean blue-sky setup."
        return {
            "distance_to_52w_high_pct": distance_to_52w_high,
            "is_52w_high": is_52w_high,
            "is_near_52w_high": is_near_52w_high,
            "status": status,
            "reason": reason,
        }

    def _build_narrative_context(
        self,
        *,
        snapshot_row: dict[str, str],
        newssentiment: str | None,
        newscore: float | None,
    ) -> dict[str, Any]:
        influencer = (snapshot_row.get("top_influencer") or "").strip() or None
        influence_type = (snapshot_row.get("influence_type") or "").strip() or None
        normalized_sentiment = (newssentiment or "").strip().lower()
        if newscore is None and not normalized_sentiment:
            status = "WATCH"
            completeness = "INCOMPLETE"
            reason = "The embedded news columns are not populated yet, so narrative conviction still needs human review."
        elif normalized_sentiment in {"positive", "bullish", "strong_positive"} and (newscore or 0.0) >= 0.6:
            status = "PASS"
            completeness = "EMBEDDED_NEWS"
            reason = "Embedded news sentiment and score support the premarket story."
        elif normalized_sentiment in {"negative", "bearish", "strong_negative"} and (newscore or 0.0) <= 0.4:
            status = "FAIL"
            completeness = "EMBEDDED_NEWS"
            reason = "The embedded news signal weakens the catalyst story for this setup."
        else:
            status = "WATCH"
            completeness = "EMBEDDED_NEWS"
            reason = "The catalyst exists, but the embedded news signal is only neutral or moderate."
        return {
            "sentiment": newssentiment,
            "score": newscore,
            "completeness": completeness,
            "top_influencer": influencer,
            "influence_type": influence_type,
            "status": status,
            "reason": reason,
        }

    def _determine_setup_status(
        self,
        *,
        setup_score: float,
        narrative_context: dict[str, Any],
        action: str,
        risk_bucket: str | None,
    ) -> str:
        if action in {"REDUCE", "EXIT"}:
            return "NOT_READY"
        if narrative_context["completeness"] == "INCOMPLETE":
            if setup_score >= 60:
                return "NEEDS_REVIEW"
            if setup_score >= 45:
                return "WATCHLIST"
            return "NOT_READY"
        if (
            setup_score >= 72
            and narrative_context["status"] in {"PASS", "WATCH"}
            and risk_bucket != "VERY_HIGH"
            and action in {"BUY", "ADD", "HOLD", "WATCH_ONLY"}
        ):
            return "HIGH_PRIORITY_SETUP"
        if setup_score >= 54:
            return "WATCHLIST"
        if setup_score >= 40 or narrative_context["status"] == "WATCH":
            return "NEEDS_REVIEW"
        return "NOT_READY"

    def _setup_priority(self, setup_status: str) -> str:
        mapping = {
            "HIGH_PRIORITY_SETUP": "Priority 1",
            "WATCHLIST": "Priority 2",
            "NEEDS_REVIEW": "Priority 3",
            "NOT_READY": "Priority 4",
        }
        return mapping.get(setup_status, "Priority 4")

    def _score_resistance_context(self, distance_pct: float | None) -> float:
        if distance_pct is None:
            return 0.0
        if distance_pct >= 0:
            return 10.0
        if distance_pct >= -3:
            return 7.5
        if distance_pct >= -6:
            return 3.0
        return -1.0

    def _score_relative_volume(self, ratio: float | None) -> float:
        if ratio is None:
            return 0.0
        if ratio >= 1.5:
            return 6.0
        if ratio >= 1.0:
            return 4.0
        if ratio >= 0.75:
            return 1.0
        return -2.0

    def _score_rsi(self, rsi: float | None) -> float:
        if rsi is None:
            return 0.0
        if rsi >= 60:
            return 4.0
        if rsi >= 55:
            return 2.0
        if rsi >= 45:
            return 0.5
        return -1.0

    def _score_blue_sky(self, context: dict[str, Any]) -> float:
        status = context["status"]
        if status == "PASS":
            return 5.0
        if status == "WATCH":
            return 2.0
        return -2.0

    def _score_squeeze(self, context: dict[str, Any]) -> float:
        status = context["status"]
        score = context["compression_score"]
        if status == "PASS":
            return min(score * 3.0, 6.0)
        if status == "WATCH":
            return min(score * 1.5, 3.0)
        return 0.0

    def _score_narrative(self, context: dict[str, Any]) -> float:
        status = context["status"]
        score = context["score"] or 0.0
        if context["completeness"] == "INCOMPLETE":
            return -2.0
        if status == "PASS":
            return 6.0 + score * 4.0
        if status == "WATCH":
            return 2.5 + score * 2.0
        return -4.0

    def _score_pattern(self, context: dict[str, Any]) -> float:
        score = context.get("score")
        if not isinstance(score, (int, float)):
            return 0.0
        if score >= 80:
            return 4.0
        if score >= 65:
            return 2.5
        if score >= 50:
            return 1.0
        return 0.0

    def _pattern_check_status(self, context: dict[str, Any]) -> str:
        confidence = (context.get("confidence") or "").upper()
        if confidence == "HIGH":
            return "PASS"
        if confidence == "MEDIUM":
            return "WATCH"
        return "FAIL"

    def _threshold_status(self, value: float | None, *, high: float, medium: float) -> str:
        if value is None:
            return "FAIL"
        if value >= high:
            return "PASS"
        if value >= medium:
            return "WATCH"
        return "FAIL"

    def _make_check(self, *, label: str, status: str, value: Any, reason: str) -> dict[str, Any]:
        return {
            "label": label,
            "status": status,
            "value": value,
            "reason": reason,
        }

    def _make_alert_message(
        self,
        *,
        symbol: str,
        setup_status: str,
        setup_priority: str,
        candidate_category: str,
        action: str,
        narrative_context: dict[str, Any],
    ) -> str:
        narrative_text = (
            "embedded news is incomplete"
            if narrative_context["completeness"] == "INCOMPLETE"
            else f"news sentiment is {narrative_context['sentiment'] or 'neutral'}"
        )
        return (
            f"{symbol} is a {setup_priority} premarket setup in {candidate_category} with action {action}. "
            f"Setup status: {setup_status}. Narrative context: {narrative_text}. "
            "Use the separate intraday system after the open to confirm timing and execution."
        )

    def _first_number(self, *values: Any) -> float | None:
        for value in values:
            parsed = parse_float(value)
            if parsed is not None:
                return parsed
        return None

    def _first_source(self, *pairs: tuple[str, Any]) -> str | None:
        for label, value in pairs:
            if parse_float(value) is not None:
                return label
        return None

    def _truthy(self, value: Any) -> bool:
        normalized = str(value or "").strip().lower()
        return normalized in {"1", "1.0", "true", "yes"}
