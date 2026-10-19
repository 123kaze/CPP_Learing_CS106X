"""纸面账本关键路径的离线测试；不访问数据源，也不写入真实纸面 CSV。"""
from __future__ import annotations

import unittest

import pandas as pd

import paper_two_asset_tracker as tracker


def state() -> dict:
    return {
        "version": "two_asset_etf_v1_paper",
        "paper_start": "2026-10-13",
        "account": 20_000,
        "fee_rate": 0.00025,
        "min_fee": 5.0,
        "cash": 20_000.0,
        "holdings": {"510300": 0, "518880": 0},
        "benchmark": {"code": "510300", "cash": 20_000.0, "shares": 0, "initialized": False},
        "initialized": False,
        "last_valuation_date": None,
    }


def panel() -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.to_datetime(["2026-10-01", "2026-10-12", "2026-10-13", "2027-01-04"]),
        "open_510300": [4.0, 4.1, 4.0, 5.0],
        "close_510300": [4.1, 4.0, 4.2, 5.1],
        "open_518880": [8.0, 8.1, 8.0, 10.0],
        "close_518880": [8.1, 8.0, 8.2, 10.1],
    })


class PaperTrackerTests(unittest.TestCase):
    def test_initial_build_buys_both_assets_in_lots(self):
        data = panel()
        day = pd.Timestamp("2026-10-13")
        bar = data.loc[data["date"] == day].iloc[0]
        events, after = tracker.execute(day, bar, data, state(), 0.0)

        buys = [event for event in events if event["event"] == "BUY"]
        self.assertEqual({event["code"] for event in buys}, {"510300", "518880"})
        self.assertTrue(all(event["shares"] % 100 == 0 for event in buys))
        self.assertTrue(after["initialized"])
        self.assertGreater(after["holdings"]["510300"], 0)
        self.assertGreater(after["holdings"]["518880"], 0)
        self.assertGreaterEqual(after["cash"], 0)
        self.assertEqual(events[-1]["event"], "MARK")

    def test_quarterly_rebalance_never_sells_more_than_held(self):
        data = panel()
        first_day = pd.Timestamp("2026-10-13")
        first_bar = data.loc[data["date"] == first_day].iloc[0]
        _, initialized = tracker.execute(first_day, first_bar, data, state(), 0.0)
        rebalance_day = pd.Timestamp("2027-01-04")
        rebalance_bar = data.loc[data["date"] == rebalance_day].iloc[0]
        events, after = tracker.execute(rebalance_day, rebalance_bar, data, initialized, 0.0)

        self.assertTrue(events)
        self.assertTrue(all(event["shares"] >= 0 for event in events))
        self.assertTrue(all(shares % 100 == 0 for shares in after["holdings"].values()))
        self.assertGreaterEqual(after["cash"], 0)

    def test_no_backfill_of_missed_initial_date(self):
        data = panel()
        missed_day = pd.Timestamp("2027-01-04")
        bar = data.loc[data["date"] == missed_day].iloc[0]
        with self.assertRaisesRegex(RuntimeError, "不能事后补录"):
            tracker.execute(missed_day, bar, data, state(), 0.0)

    def test_dividend_is_credited_before_rebalance(self):
        data = panel()
        first_day = pd.Timestamp("2026-10-13")
        first_bar = data.loc[data["date"] == first_day].iloc[0]
        _, initialized = tracker.execute(first_day, first_bar, data, state(), 0.0)
        rebalance_day = pd.Timestamp("2027-01-04")
        rebalance_bar = data.loc[data["date"] == rebalance_day].iloc[0]
        held_before = initialized["holdings"]["510300"]
        cash_before = initialized["cash"]
        events, after = tracker.execute(
            rebalance_day, rebalance_bar, data, initialized, 0.0,
            [(pd.Timestamp("2026-12-15"), "510300", held_before * 0.1)],
        )

        dividends = [event for event in events if event["event"] == "DIVIDEND"]
        self.assertEqual(len(dividends), 1)
        self.assertEqual(dividends[0]["code"], "510300")
        self.assertAlmostEqual(dividends[0]["cash"], cash_before + held_before * 0.1, places=2)
        self.assertGreaterEqual(after["cash"], 0)

    def test_benchmark_is_independent_buy_and_hold_with_dividends(self):
        data = panel()
        first_day = pd.Timestamp("2026-10-13")
        first_bar = data.loc[data["date"] == first_day].iloc[0]
        initial_state = state()
        events, initialized = tracker.execute_benchmark(first_day, first_bar, initial_state)

        buys = [event for event in events if event["event"] == "BENCHMARK_BUY"]
        self.assertEqual(len(buys), 1)
        self.assertEqual(buys[0]["shares"] % 100, 0)
        self.assertTrue(initialized["benchmark"]["initialized"])
        held = initialized["benchmark"]["shares"]

        later_day = pd.Timestamp("2027-01-04")
        later_bar = data.loc[data["date"] == later_day].iloc[0]
        later_events, after = tracker.execute_benchmark(
            later_day, later_bar, initialized,
            [(pd.Timestamp("2026-12-15"), "510300", held * 0.1)],
        )
        self.assertEqual(after["benchmark"]["shares"], held)
        self.assertTrue(any(event["event"] == "BENCHMARK_DIVIDEND" for event in later_events))
        marks = [event for event in later_events if event["event"] == "BENCHMARK_MARK"]
        self.assertEqual(len(marks), 1)
        self.assertGreater(float(marks[0]["equity"]), 0)

    def test_missed_quarterly_rebalance_is_detected(self):
        data = panel()
        missed = tracker.missed_rebalance_days(
            data, pd.Timestamp("2026-10-13"), pd.Timestamp("2027-01-05"))
        self.assertEqual(missed, [pd.Timestamp("2027-01-04")])


if __name__ == "__main__":
    unittest.main()
