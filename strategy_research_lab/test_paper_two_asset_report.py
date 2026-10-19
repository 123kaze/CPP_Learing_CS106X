"""纸面报告的离线集成测试；不访问网络且只使用临时账本。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import paper_two_asset_report as report
import paper_two_asset_tracker as tracker


def fresh_state() -> dict:
    return {
        "version": "two_asset_etf_v1_paper",
        "paper_start": "2026-10-13",
        "account": 20_000.0,
        "fee_rate": 0.00025,
        "min_fee": 5.0,
        "cash": 20_000.0,
        "holdings": {"510300": 0, "518880": 0},
        "benchmark": {"code": "510300", "cash": 20_000.0, "shares": 0, "initialized": False},
        "initialized": False,
        "last_valuation_date": None,
    }


def fixture_panel() -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.to_datetime(["2026-10-13", "2027-01-04"]),
        "open_510300": [4.0, 5.0], "close_510300": [4.2, 5.1],
        "open_518880": [8.0, 10.0], "close_518880": [8.2, 10.1],
    })


class PaperReportTests(unittest.TestCase):
    def test_report_tracks_costs_dividends_and_relative_return(self):
        data = fixture_panel()
        state = fresh_state()
        first = data.iloc[0]
        events, state = tracker.execute(pd.Timestamp("2026-10-13"), first, data, state, 0.0)
        benchmark_events, state = tracker.execute_benchmark(pd.Timestamp("2026-10-13"), first, state)

        later = data.iloc[1]
        held = state["holdings"]["510300"]
        later_events, state = tracker.execute(
            pd.Timestamp("2027-01-04"), later, data, state, 0.0,
            [(pd.Timestamp("2026-12-15"), "510300", held * 0.1)],
        )
        benchmark_later, state = tracker.execute_benchmark(
            pd.Timestamp("2027-01-04"), later, state,
            [(pd.Timestamp("2026-12-15"), "510300", state["benchmark"]["shares"] * 0.1)],
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log, state_path = root / "paper.csv", root / "state.json"
            tracker.append_events(log, [*events, *benchmark_events, *later_events, *benchmark_later])
            state_path.write_text(json.dumps(state), encoding="utf-8")
            outcome = report.build_report(log, state_path)

        self.assertEqual(outcome["status"], "tracking")
        self.assertEqual(outcome["portfolio"]["observed_valuations"], 2)
        self.assertEqual(outcome["benchmark_510300_buy_and_hold"]["observed_valuations"], 2)
        self.assertGreater(outcome["costs_and_cash_dividends"]["portfolio_dividend_cash"], 0)
        self.assertGreater(outcome["costs_and_cash_dividends"]["benchmark_dividend_cash"], 0)
        self.assertGreaterEqual(outcome["costs_and_cash_dividends"]["portfolio_commission"], 10)

    def test_empty_ledger_is_not_started(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log, state_path = root / "paper.csv", root / "state.json"
            tracker.append_events(log, [])
            state_path.write_text(json.dumps(fresh_state()), encoding="utf-8")
            outcome = report.build_report(log, state_path)
        self.assertEqual(outcome["status"], "not_started")


if __name__ == "__main__":
    unittest.main()
