from __future__ import annotations

import shutil
import unittest
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from core.daily_edge import DailyEdgeService, DailySnapshotPoint


ROOT_HEADER = (
    "ticker,snapshot_date,gnn_prob,selected_category,trading_action,trend_score,risk_bucket,ref_name,ref_industry\n"
)

SNAPSHOT_HEADER = (
    "ticker,snapshot_date,day_close,day_volume,day_high,day_low,high_20d,low_20d,vwap,rsi14,ref_name,ref_industry\n"
)


class DailyEdgeFixtureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = (
            Path(__file__).resolve().parents[1] / "_test_tmp" / f"daily_edge_{uuid4().hex}"
        )
        self.tempdir.mkdir(parents=True, exist_ok=False)
        (self.tempdir / "snapshot").mkdir()
        self._write_root_snapshot()
        self._write_daily_snapshots()

    def tearDown(self) -> None:
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def _write_root_snapshot(self) -> None:
        trade_date = date(2026, 2, 9).isoformat()
        rows = [
            f"AAA,{trade_date},0.92,Aggressive Breakouts,BUY,0.81,LOW,Alpha Software,Software Infrastructure",
            f"BBB,{trade_date},0.84,Balanced Momentum,BUY,0.75,MEDIUM,Beta Software,Software Applications",
            f"CCC,{trade_date},0.41,Ultra-Conservative,WATCH_ONLY,0.32,HIGH,Capital Utility,Utilities",
            f"DDD,{trade_date},0.66,Rare Category,BUY,0.58,LOW,Delta Labs,Biotech",
        ]
        (self.tempdir / "MarketSnapshot_output.csv").write_text(
            ROOT_HEADER + "\n".join(rows) + "\n",
            encoding="utf-8",
        )

    def _write_daily_snapshots(self) -> None:
        start = date(2026, 1, 1)
        for offset in range(40):
            current_day = start + timedelta(days=offset)
            lines = [SNAPSHOT_HEADER.rstrip()]

            spy_close = 100.0 + (offset * 0.20)
            xlk_close = 100.0 + (offset * 0.25)
            aaa_close = 50.0 + (offset * 0.65)
            bbb_close = 30.0 + (offset * 0.60)
            ccc_close = 40.0 + (offset * 0.12)

            lines.append(self._snapshot_row("SPY", current_day, spy_close, 1000, spy_close + 1.1, spy_close - 1.2, spy_close - 0.3, spy_close - 4.0, spy_close - 0.2, 55 + (offset * 0.1), "SPY ETF", "Broad Market"))
            lines.append(self._snapshot_row("XLK", current_day, xlk_close, 900, xlk_close + 1.0, xlk_close - 1.1, xlk_close - 0.2, xlk_close - 4.0, xlk_close - 0.25, 57 + (offset * 0.1), "XLK ETF", "Technology"))
            lines.append(self._snapshot_row("AAA", current_day, aaa_close, 1800 + (offset * 35), aaa_close + 0.2, aaa_close - 0.8, aaa_close - 0.45, aaa_close - 5.5, aaa_close - 0.35, 64 + (offset * 0.12), "Alpha Software", "Software Infrastructure"))
            lines.append(self._snapshot_row("BBB", current_day, bbb_close, 900 - ((offset % 5) * 80), bbb_close + 0.2, bbb_close - 0.9, bbb_close - 0.30, bbb_close - 4.0, bbb_close - 0.25, 63 + (offset * 0.10), "Beta Software", "Software Applications"))
            lines.append(self._snapshot_row("CCC", current_day, ccc_close, 500, ccc_close + 0.6, ccc_close - 0.8, ccc_close + 1.25, ccc_close - 3.0, ccc_close + 0.25, 42 + (offset * 0.04), "Capital Utility", "Utilities"))

            if offset >= 16:
                ddd_close = 25.0 + ((offset - 16) * 0.45)
                lines.append(self._snapshot_row("DDD", current_day, ddd_close, 650 + (offset * 5), ddd_close + 0.9, ddd_close - 0.7, ddd_close - 0.25, ddd_close - 3.0, ddd_close - 0.2, 61 + (offset * 0.06), "Delta Labs", "Biotech"))

            (self.tempdir / "snapshot" / f"stock_snapshot_{current_day.isoformat()}.csv").write_text(
                "\n".join(lines) + "\n",
                encoding="utf-8",
            )

    def _snapshot_row(
        self,
        ticker: str,
        snapshot_date: date,
        close_value: float,
        volume: float,
        high_value: float,
        low_value: float,
        high_20d: float,
        low_20d: float,
        vwap: float,
        rsi14: float,
        ref_name: str,
        ref_industry: str,
    ) -> str:
        return ",".join(
            [
                ticker,
                snapshot_date.isoformat(),
                f"{close_value:.2f}",
                f"{volume:.2f}",
                f"{high_value:.2f}",
                f"{low_value:.2f}",
                f"{high_20d:.2f}",
                f"{low_20d:.2f}",
                f"{vwap:.2f}",
                f"{rsi14:.2f}",
                ref_name,
                ref_industry,
            ]
        )

    def test_service_builds_patterns_validator_and_expectancy(self) -> None:
        service = DailyEdgeService(self.tempdir)
        candidates = {candidate.symbol: candidate for candidate in service.list_candidates(limit=10)}

        aaa = candidates["AAA"]
        self.assertIn(aaa.pattern_context["family"], {"Momentum Expansion", "High-Ground Leader"})
        self.assertEqual("FULL_VALIDATION", aaa.validator_context["validator_profile"])
        self.assertGreater(aaa.expectancy_context["sample_size"], 0)
        self.assertIn(aaa.setup_status, {"HIGH_PRIORITY_SETUP", "WATCHLIST"})
        self.assertEqual("BREAKOUT", aaa.trade_plan_context["entry_mode"])
        self.assertGreater(aaa.trade_plan_context["target_entry_price"], aaa.current_price)
        self.assertLess(aaa.trade_plan_context["stop_loss_price"], aaa.trade_plan_context["target_entry_price"])
        self.assertGreater(aaa.trade_plan_context["take_profit_price"], aaa.trade_plan_context["target_entry_price"])

    def test_validator_profiles_cover_volume_lag_and_fail(self) -> None:
        service = DailyEdgeService(self.tempdir)
        candidates = {candidate.symbol: candidate for candidate in service.list_candidates(limit=10)}

        self.assertEqual("VOLUME_LAG", candidates["BBB"].validator_context["validator_profile"])
        self.assertEqual("FAILED", candidates["CCC"].validator_context["validator_profile"])
        self.assertEqual("PULLBACK", candidates["CCC"].trade_plan_context["entry_mode"])
        self.assertLessEqual(candidates["CCC"].trade_plan_context["target_entry_price"], candidates["CCC"].current_price)
        self.assertLess(candidates["CCC"].trade_plan_context["stop_loss_price"], candidates["CCC"].trade_plan_context["target_entry_price"])
        self.assertGreater(candidates["CCC"].trade_plan_context["take_profit_price"], candidates["CCC"].trade_plan_context["target_entry_price"])

    def test_expectancy_falls_back_to_global_when_exact_group_is_sparse(self) -> None:
        service = DailyEdgeService(self.tempdir)
        candidates = {candidate.symbol: candidate for candidate in service.list_candidates(limit=10)}

        ddd = candidates["DDD"]
        self.assertIn(ddd.expectancy_context["fallback_level"], {"pattern_family", "global"})
        self.assertGreaterEqual(ddd.expectancy_context["sample_size"], 8)

    def test_category_profiles_change_reward_distance(self) -> None:
        service = DailyEdgeService(self.tempdir)
        candidates = {candidate.symbol: candidate for candidate in service.list_candidates(limit=10)}

        aaa = candidates["AAA"].trade_plan_context
        bbb = candidates["BBB"].trade_plan_context
        aaa_reward = aaa["take_profit_price"] - aaa["target_entry_price"]
        bbb_reward = bbb["take_profit_price"] - bbb["target_entry_price"]
        aaa_risk = aaa["target_entry_price"] - aaa["stop_loss_price"]
        bbb_risk = bbb["target_entry_price"] - bbb["stop_loss_price"]

        self.assertGreater(aaa_reward / aaa_risk, bbb_reward / bbb_risk)

    def test_volatility_fallback_uses_daily_range_proxy(self) -> None:
        service = DailyEdgeService(self.tempdir)
        aaa = {candidate.symbol: candidate for candidate in service.list_candidates(limit=10)}["AAA"]

        self.assertGreater(aaa.historical_metrics["avg_daily_range_14d"], 0)
        self.assertGreater(aaa.trade_plan_context["risk_unit_price"], 0)

    def test_outcome_sample_calculates_end_return_mfe_and_mae(self) -> None:
        service = DailyEdgeService(self.tempdir)
        future_points = []
        base_day = date(2026, 3, 1)
        closes = [103, 105, 106, 104, 108, 110, 109, 111, 112, 115]
        highs = [104, 106, 107, 105, 109, 111, 110, 112, 113, 116]
        lows = [99, 101, 102, 100, 103, 106, 105, 107, 108, 110]
        for idx in range(10):
            future_points.append(
                DailySnapshotPoint(
                    ticker="ZZZ",
                    snapshot_date=base_day + timedelta(days=idx),
                    day_close=closes[idx],
                    day_volume=1000,
                    day_high=highs[idx],
                    day_low=lows[idx],
                    high_20d=None,
                    low_20d=None,
                    vwap=None,
                    rsi14=None,
                    ref_name=None,
                    ref_industry=None,
                )
            )

        sample = service._build_outcome_sample(
            ticker="ZZZ",
            category="Aggressive Breakouts",
            pattern_family="Momentum Expansion",
            validator_profile="FULL_VALIDATION",
            entry_price=100.0,
            future_points=future_points,
        )
        assert sample is not None
        self.assertAlmostEqual(5.0, sample["horizons"][2]["end_return_pct"], places=4)
        self.assertAlmostEqual(6.0, sample["horizons"][2]["mfe_pct"], places=4)
        self.assertAlmostEqual(-1.0, sample["horizons"][2]["mae_pct"], places=4)
        self.assertAlmostEqual(8.0, sample["horizons"][5]["end_return_pct"], places=4)
        self.assertAlmostEqual(15.0, sample["horizons"][10]["end_return_pct"], places=4)


class RealDatasetSmokeTest(unittest.TestCase):
    def test_real_service_returns_expanded_candidates(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        if not (project_root / "MarketSnapshot_output.csv").exists():
            self.skipTest("Root snapshot not available for real dataset smoke test.")
        if not list((project_root / "snapshot").glob("stock_snapshot_*.csv")):
            self.skipTest("Historical snapshot files not available for real dataset smoke test.")
        service = DailyEdgeService(project_root)
        first = service.list_candidates(limit=1)[0]
        payload = first.to_dict()

        self.assertIn("pattern_context", payload)
        self.assertIn("validator_context", payload)
        self.assertIn("expectancy_context", payload)
        self.assertIn("trade_plan_context", payload)
        self.assertIn("setup_score", payload)
        self.assertIn("setup_status", payload)
        self.assertIn("target_entry_price", payload)
        self.assertIn("take_profit_price", payload)
        self.assertIn("stop_loss_price", payload)




