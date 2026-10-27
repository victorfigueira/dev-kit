#!/usr/bin/env python3
"""Unit tests for dev-kit cost tracker."""
import os
import unittest
from tools.cost_tracker import (
    calculate_cost,
    detect_active_model,
    log_ticket_completion,
    get_ledger_file_path,
    get_costs_md_path
)


class TestCostTracker(unittest.TestCase):
    def test_calculate_cost_claude_sonnet(self):
        # 1M input ($3.00) + 1M output ($15.00) = $18.00
        cost = calculate_cost(1_000_000, 1_000_000, "claude-3-7-sonnet")
        self.assertAlmostEqual(cost, 18.00, places=3)

    def test_calculate_cost_gemini_flash(self):
        # 1M input ($0.10) + 1M output ($0.40) = $0.50
        cost = calculate_cost(1_000_000, 1_000_000, "gemini-2.0-flash")
        self.assertAlmostEqual(cost, 0.50, places=3)

    def test_detect_active_model(self):
        self.assertEqual(detect_active_model("claude-3-5-sonnet-20241022"), "claude-3-5-sonnet-20241022")
        self.assertEqual(detect_active_model("gemini-2.0-flash"), "gemini-2.0-flash")
        self.assertEqual(detect_active_model("gemini 3.8 flash medium"), "gemini 3.8 flash medium")

        from unittest.mock import patch
        with patch.dict("os.environ", {}, clear=True):
            with patch("tools.cost_tracker.detect_antigravity_model", return_value=None):
                self.assertEqual(detect_active_model(), "claude-3-7-sonnet")

        with patch("tools.cost_tracker.detect_antigravity_model", return_value="Gemini 3.8 Flash (Medium)"):
            self.assertEqual(detect_active_model(), "Gemini 3.8 Flash (Medium)")

    def test_log_ticket_completion(self):
        entry = log_ticket_completion(
            ticket_key="TEST-101",
            summary="Test ticket logging",
            branch="feat/TEST-101-test",
            post_jira=False
        )
        self.assertEqual(entry["ticket"], "TEST-101")
        self.assertTrue(entry["total_tokens"] > 0)
        self.assertTrue(entry["cost_usd"] > 0)
        self.assertTrue(os.path.exists(get_ledger_file_path()))
        self.assertTrue(os.path.exists(get_costs_md_path()))


if __name__ == "__main__":
    unittest.main()
