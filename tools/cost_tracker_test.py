#!/usr/bin/env python3
"""Unit tests for dev-kit cost tracker."""
import unittest
from tools.cost_tracker import calculate_cost, detect_active_model


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
        self.assertEqual(detect_active_model("claude-3-5-sonnet-20241022"), "claude-3-5-sonnet")
        self.assertEqual(detect_active_model("gemini-2.0-flash"), "gemini-2.0-flash")
        self.assertEqual(detect_active_model("unknown-model"), "claude-3-7-sonnet")


if __name__ == "__main__":
    unittest.main()
