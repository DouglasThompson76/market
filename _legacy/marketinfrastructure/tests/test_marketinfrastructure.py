from __future__ import annotations

import json
import shutil
import unittest
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from marketinfrastructure.data import MarketDataRepository
from marketinfrastructure.service import MarketInfrastructureService


MARKET_SNAPSHOT = """ticker,snapshot_date,gnn_prob,selected_category,trading_action,management_action,risk_bucket,top_influencer,influence_type,day_current_price,day_vwap,high_20d,high_50d,high_52w,trend_rsi14,day_volume,trend_close,trend_volume,range_20d,range_50d,trend_vol_20d,trend_vol_50d,dist_from_52w_high_pct,ref_name,ref_industry,trend_score,newssentiment,newscore
AAA,2026-03-25,0.91,Aggressive Breakouts,BUY,BUY,MEDIUM,AAA,lead_lag,101,99,105,105,105,62,150000,102,140000,6,10,100000,140000,-2,Alpha Corp,Software,0.88,positive,0.84
BBB,2026-03-25,0.42,Ultra-Conservative,WATCH_ONLY,WATCH_ONLY,HIGH,BBB,statistical,,,,44,45,48,,41,48000,5,8,45000,60000,-8,Beta Corp,Utilities,0.33,,
CCC,2026-03-25,0.95,Aggressive Breakouts,REDUCE,REDUCE,LOW,CCC,lead_lag,205,204,210,210,212,68,250000,206,210000,5,9,180000,220000,-1,Gamma Corp,Technology,0.97,positive,0.91
"""

SNAPSHOT_DAY_1 = """ticker,snapshot_date,day_close,day_volume,day_high,day_low,high_20d,low_20d,vwap,rsi14,ref_name,ref_industry
AAA,2026-03-21,95,100000,104.2,90,103,80,94,58,Alpha Corp,Software
BBB,2026-03-21,40,70000,41,36,45,30,39,46,Beta Corp,Utilities
CCC,2026-03-21,198,180000,208.5,190,209,180,197,64,Gamma Corp,Technology
"""

SNAPSHOT_DAY_2 = """ticker,snapshot_date,day_close,day_volume,day_high,day_low,high_20d,low_20d,vwap,rsi14,ref_name,ref_industry
AAA,2026-03-24,100,120000,104.8,92,104,81,98,60,Alpha Corp,Software
BBB,2026-03-24,42,50000,43,37,44,31,41,47,Beta Corp,Utilities
CCC,2026-03-24,203,195000,209.2,194,210,181,201,66,Gamma Corp,Technology
"""

SNAPSHOT_DAY_3 = """ticker,snapshot_date,day_close,day_volume,day_high,day_low,high_20d,low_20d,vwap,rsi14,ref_name,ref_industry
AAA,2026-03-25,102,140000,104.9,97,105,82,100,64,Alpha Corp,Software
BBB,2026-03-25,41,48000,42,38,44,31,40,49,Beta Corp,Utilities
CCC,2026-03-25,206,210000,210,198,210,182,205,68,Gamma Corp,Technology
"""


class MarketInfrastructureFixtureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = (
            Path(__file__).resolve().parents[2] / "_test_tmp" / f"mi_fixture_{uuid4().hex}"
        )
        self.tempdir.mkdir(parents=True, exist_ok=False)
        root = self.tempdir
        (root / "snapshot").mkdir()
        (root / "marketinfrastructure" / "trades").mkdir(parents=True)
        (root / "MarketSnapshot_output.csv").write_text(MARKET_SNAPSHOT, encoding="utf-8")
        (root / "snapshot" / "stock_snapshot_2026-03-21.csv").write_text(
            SNAPSHOT_DAY_1, encoding="utf-8"
        )
        (root / "snapshot" / "stock_snapshot_2026-03-24.csv").write_text(
            SNAPSHOT_DAY_2, encoding="utf-8"
        )
        (root / "snapshot" / "stock_snapshot_2026-03-25.csv").write_text(
            SNAPSHOT_DAY_3, encoding="utf-8"
        )
        self.root = root

    def tearDown(self) -> None:
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_builds_candidates_and_backfills_history(self) -> None:
        service = MarketInfrastructureService(project_root=self.root)
        candidates = service.list_candidates(limit=10)
        self.assertEqual(3, len(candidates))

        aaa = service.get_candidate("AAA", "2026-03-25")
        self.assertIsNotNone(aaa)
        assert aaa is not None
        self.assertEqual("HIGH_PRIORITY_SETUP", aaa.setup_status)
        self.assertEqual("PASS", aaa.narrative_context["status"])
        self.assertAlmostEqual(120000.0, aaa.relative_volume_context["avg_volume_5d"], places=2)
        self.assertEqual("PASS", aaa.favor_checks_local["gnn_support"]["status"])
        self.assertEqual("Priority 1", aaa.setup_priority)
        self.assertEqual("trend_close", aaa.current_price_context["source"])
        self.assertEqual("trend_volume_vs_snapshot_history_5d_avg", aaa.relative_volume_context["source"])
        self.assertEqual(3, aaa.pink_line_context["touch_count_90d"])
        self.assertEqual("PASS", aaa.pink_line_context["status"])

        bbb = service.get_candidate("BBB", "2026-03-25")
        self.assertIsNotNone(bbb)
        assert bbb is not None
        self.assertEqual("NOT_READY", bbb.setup_status)
        self.assertEqual("INCOMPLETE", bbb.narrative_context["completeness"])
        self.assertEqual("trend_rsi14", bbb.daily_rsi_context["source"])
        self.assertEqual("snapshot_history.resistance_20d", bbb.resistance_20d["source"])

        ccc = service.get_candidate("CCC", "2026-03-25")
        self.assertIsNotNone(ccc)
        assert ccc is not None
        self.assertEqual("NOT_READY", ccc.setup_status)
        self.assertEqual("REDUCE", ccc.trading_action)

    def test_candidate_output_stays_premarket_only(self) -> None:
        service = MarketInfrastructureService(project_root=self.root)
        aaa = service.get_candidate("AAA", "2026-03-25")
        self.assertIsNotNone(aaa)
        assert aaa is not None
        self.assertTrue(aaa.requires_intraday_confirmation)
        self.assertIn("separate intraday system", aaa.handoff_message)
        self.assertIn("premarket setup", aaa.alert_message.lower())

    def test_candidate_sorting_supports_price_and_gnn(self) -> None:
        service = MarketInfrastructureService(project_root=self.root)
        by_price = service.list_candidates(sort_by="price", sort_dir="desc", limit=3)
        self.assertEqual(["CCC", "AAA", "BBB"], [candidate.symbol for candidate in by_price])

        by_gnn = service.list_candidates(sort_by="gnn", sort_dir="asc", limit=3)
        self.assertEqual(["BBB", "AAA", "CCC"], [candidate.symbol for candidate in by_gnn])

    def test_pattern_intelligence_surfaces_family_and_score(self) -> None:
        service = MarketInfrastructureService(project_root=self.root)
        aaa = service.get_candidate("AAA", "2026-03-25")
        self.assertIsNotNone(aaa)
        assert aaa is not None
        self.assertIn(
            aaa.pattern_context["family"],
            {"Coiled Breakout", "High-Ground Leader", "Pressure Builder", "Momentum Expansion", "Range Repair"},
        )
        self.assertIsInstance(aaa.pattern_context["score"], float)
        self.assertIn(aaa.pattern_context["confidence"], {"HIGH", "MEDIUM", "LOW"})

    def test_history_loader_uses_ninety_day_window(self) -> None:
        root = self.tempdir / "history_window_case"
        (root / "snapshot").mkdir(parents=True)
        (root / "MarketSnapshot_output.csv").write_text(
            "ticker,snapshot_date,gnn_prob,selected_category,trading_action,management_action,risk_bucket,top_influencer,influence_type\nAAA,2026-03-25,0.5,Aggressive Breakouts,BUY,BUY,LOW,AAA,lead_lag\n",
            encoding="utf-8",
        )
        start = date(2026, 2, 1)
        for offset in range(40):
            day = start + timedelta(days=offset)
            content = (
                "ticker,snapshot_date,day_close,day_volume,day_high,day_low,high_20d,low_20d,vwap,rsi14,ref_name,ref_industry\n"
                f"AAA,{day.isoformat()},100,1000,105,95,105,95,100,55,Alpha Corp,Software\n"
            )
            (root / "snapshot" / f"stock_snapshot_{day.isoformat()}.csv").write_text(
                content,
                encoding="utf-8",
            )

        repository = MarketDataRepository(root)
        history = repository.load_history_by_ticker({date(2026, 3, 25)})
        self.assertEqual(40, len(history["AAA"]))


class RealProjectSmokeTest(unittest.TestCase):
    def test_real_project_data_loads(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        service = MarketInfrastructureService(project_root=project_root)
        candidates = service.list_candidates(limit=5)
        self.assertTrue(candidates)
        self.assertIn(
            candidates[0].setup_status,
            {
                "HIGH_PRIORITY_SETUP",
                "WATCHLIST",
                "NEEDS_REVIEW",
                "NOT_READY",
            },
        )
        self.assertEqual("INCOMPLETE", candidates[0].narrative_context["completeness"])
