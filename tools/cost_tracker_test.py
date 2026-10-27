#!/usr/bin/env python3
"""Unit tests for dev-kit cost tracker."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from tools import cost_tracker

MEASURED = {
    "available": True,
    "estimated": False,
    "source": "Claude Code session files",
    "since": "2026-10-27T10:00:00Z",
    "models": ["claude-opus-5-5"],
    "pricing": {"claude-opus-5-5": "Claude Opus 5.5"},
    "pricing_as_of": "2026-10-27",
    "totals": {"input_tokens": 100, "output_tokens": 50, "cache_creation_input_tokens": 0,
               "cache_read_input_tokens": 0, "total_tokens": 150},
    "cost_usd": 0.0014,
    "agents": [{"agent": "orchestrator", "name": "Orchestrator (main session)", "runs": 1,
                "input_tokens": 100, "output_tokens": 50, "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0, "total_tokens": 150, "cost_usd": 0.0014}],
    "notes": "",
}


class TestCostTracker(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def test_calculate_cost_current_models(self):
        # Opus 5.5: 1M input ($4) + 1M output ($20)
        self.assertAlmostEqual(cost_tracker.calculate_cost(1_000_000, 1_000_000, "claude-opus-5-5"), 24.00, places=3)
        # Gemini 3.8 Flash introductory: $0.75 + $3.75
        self.assertAlmostEqual(cost_tracker.calculate_cost(1_000_000, 1_000_000, "Gemini 3.8 Flash (High)"), 4.50, places=3)

    def test_detect_active_model_has_no_hardcoded_default(self):
        self.assertEqual(cost_tracker.detect_active_model("claude-sonnet-5-5"), "claude-sonnet-5-5")
        with patch.dict(os.environ, {}, clear=True), \
                patch("tools.cost_tracker.usage_report.detect_model", return_value=None):
            self.assertIsNone(cost_tracker.detect_active_model())
        with patch.dict(os.environ, {"DEV_KIT_MODEL": "claude-haiku-5-5"}):
            self.assertEqual(cost_tracker.detect_active_model(), "claude-haiku-5-5")

    def test_start_records_since_used_by_report(self):
        data = cost_tracker.start_ticket("PAS-1")
        with patch("tools.cost_tracker.usage_report.collect", return_value=MEASURED) as collect:
            report = cost_tracker.generate_cost_report()
        collect.assert_called_once_with(os.getcwd(), data["since"])
        self.assertFalse(report["estimated"])

    def test_falls_back_to_marked_estimate(self):
        cost_tracker.start_ticket("PAS-1")
        with patch("tools.cost_tracker.usage_report.collect", return_value={"available": False}), \
                patch("tools.cost_tracker.usage_report.detect_model", return_value=None):
            report = cost_tracker.generate_cost_report()
        self.assertTrue(report["estimated"])
        self.assertIn("Estimated", cost_tracker.format_markdown(report))

    def test_log_marks_estimate_in_ledger_and_costs_md(self):
        with patch("tools.cost_tracker.usage_report.collect", return_value={"available": False}), \
                patch("tools.cost_tracker.usage_report.detect_model", return_value=None):
            entry = cost_tracker.log_ticket_completion("TEST-1", "Estimated ticket", post_jira=False)
        self.assertTrue(entry["estimated"])
        self.assertTrue(entry["cost_usd"] > 0)
        with open(cost_tracker.get_costs_md_path()) as f:
            self.assertIn("| estimated |", f.read())

    def test_log_measured_entry_and_resets_session(self):
        cost_tracker.start_ticket("TEST-2")
        with patch("tools.cost_tracker.usage_report.collect", return_value=MEASURED):
            entry = cost_tracker.log_ticket_completion("TEST-2", "Measured ticket", post_jira=False)
        self.assertFalse(entry["estimated"])
        self.assertEqual(entry["roles"]["orchestrator"]["tokens"], 150)
        with open(cost_tracker.get_ledger_file_path()) as f:
            self.assertEqual(json.load(f)[0]["ticket"], "TEST-2")
        with open(cost_tracker.get_costs_md_path()) as f:
            self.assertIn("| measured |", f.read())
        self.assertFalse(os.path.exists(cost_tracker.get_session_file_path()))

    def test_jira_comment_says_estimated(self):
        with patch("tools.cost_tracker.usage_report.collect", return_value={"available": False}), \
                patch("tools.cost_tracker.usage_report.detect_model", return_value=None), \
                patch("jira_sync.comment_ticket") as comment:
            cost_tracker.log_ticket_completion("TEST-3", post_jira=True)
        self.assertIn("(estimated)", comment.call_args[0][1])


if __name__ == "__main__":
    unittest.main()
