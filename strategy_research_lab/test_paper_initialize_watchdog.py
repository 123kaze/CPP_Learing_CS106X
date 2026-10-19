"""守护的时间门控测试：数据日前/后绝不触发纸面提交。"""
from __future__ import annotations

import subprocess
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import paper_initialize_watchdog as watchdog


TZ = ZoneInfo("Asia/Shanghai")


class WatchdogTests(unittest.TestCase):
    def test_only_target_evening_can_invoke_tracker(self):
        with patch.object(watchdog, "read_initialized", return_value=False), \
                patch.object(watchdog.subprocess, "run") as run:
            self.assertEqual(watchdog.run_once(datetime(2026, 10, 12, 20, 0, tzinfo=TZ)), 0)
            self.assertEqual(watchdog.run_once(datetime(2026, 10, 13, 15, 59, tzinfo=TZ)), 0)
            self.assertEqual(watchdog.run_once(datetime(2026, 10, 14, 16, 0, tzinfo=TZ)), 1)
            run.assert_not_called()

    def test_target_window_invokes_only_local_paper_tracker(self):
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout="preview\n", stderr="")
        with patch.object(watchdog, "read_initialized", return_value=False), \
                patch.object(watchdog.subprocess, "run", return_value=result) as run:
            self.assertEqual(watchdog.run_once(datetime(2026, 10, 13, 16, 0, tzinfo=TZ)), 0)
        command = run.call_args.args[0]
        self.assertEqual(command[0], __import__("sys").executable)
        self.assertEqual(command[-3:], ["--as-of", "20261013", "--commit"])

    def test_initialized_account_never_invokes_tracker(self):
        with patch.object(watchdog, "read_initialized", return_value=True), \
                patch.object(watchdog.subprocess, "run") as run:
            self.assertEqual(watchdog.run_once(datetime(2026, 10, 13, 16, 0, tzinfo=TZ)), 0)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
