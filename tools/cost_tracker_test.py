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

    def test_log_marks_estimate_in_runs_and_costs_md(self):
        with patch("tools.cost_tracker.usage_report.collect", return_value={"available": False}), \
                patch("tools.cost_tracker.usage_report.detect_model", return_value=None):
            run = cost_tracker.log_ticket_completion("TEST-1", "Estimated ticket", branch="feat/TEST-1", post_jira=False)
        self.assertTrue(run["estimated"])
        self.assertTrue(run["cost_usd"] > 0)
        with open(cost_tracker.get_costs_md_path()) as f:
            self.assertIn("| estimated |", f.read())

    def test_run_record_has_the_documented_fields(self):
        cost_tracker.start_ticket("TEST-2")
        with patch("tools.cost_tracker.usage_report.collect", return_value=MEASURED), \
                patch.dict(os.environ, {"CLAUDECODE": "1"}):
            run = cost_tracker.log_ticket_completion("TEST-2", "Measured ticket", branch="feat/TEST-2", post_jira=False,
                                                     base_branch="develop", qa_rounds=2, ac="3/3")
        with open(cost_tracker.get_runs_file_path()) as f:
            data = json.load(f)
        self.assertEqual(data["schema_version"], 1)
        saved = data["runs"][0]
        for key in ("ticket", "summary", "branch", "base_branch", "commit", "kit_version", "tool", "model",
                    "started_at", "finished_at", "qa", "estimated", "cost_usd", "usage", "delivery"):
            self.assertIn(key, saved)
        self.assertEqual(saved["tool"], "Claude Code")
        self.assertEqual(saved["base_branch"], "develop")
        self.assertEqual(saved["qa"], {"verdict": "APPROVED", "rounds": 2,
                                       "acceptance_criteria": {"verified": 3, "total": 3}})
        self.assertEqual(saved["started_at"], "2026-10-27T10:00:00Z")
        self.assertEqual(saved["usage"]["agents"][0]["agent"], "orchestrator")
        with open(os.path.join(cost_tracker.KIT_DIR, "VERSION")) as f:
            self.assertEqual(saved["kit_version"], f.read().strip())
        self.assertFalse(run["estimated"])
        self.assertFalse(os.path.exists(cost_tracker.get_session_file_path()))

    def test_costs_md_is_generated_from_runs(self):
        with patch("tools.cost_tracker.usage_report.collect", return_value=MEASURED):
            cost_tracker.start_ticket("A-1")
            cost_tracker.log_ticket_completion("A-1", "First", branch="feat/A-1", post_jira=False, qa_rounds=1)
            cost_tracker.start_ticket("A-1")
            cost_tracker.log_ticket_completion("A-1", "First again", branch="feat/A-1", post_jira=False, qa_rounds=3)
        with open(cost_tracker.get_runs_file_path()) as f:
            runs = json.load(f)["runs"]
        self.assertEqual(len(runs), 1)  # same ticket and branch replaces the record
        os.remove(cost_tracker.get_costs_md_path())
        cost_tracker.render_costs_markdown(runs)
        with open(cost_tracker.get_costs_md_path()) as f:
            md = f.read()
        self.assertIn("First again", md)
        self.assertIn("| 3 |", md)
        self.assertIn("| measured |", md)

    def test_deliver_updates_latest_run(self):
        with patch("tools.cost_tracker.usage_report.collect", return_value=MEASURED):
            cost_tracker.start_ticket("B-1")
            cost_tracker.log_ticket_completion("B-1", branch="feat/B-1", post_jira=False)
        run = cost_tracker.record_delivery("B-1", pushed=True, jira_status="In Review")
        self.assertEqual(run["delivery"], {"pushed": True, "jira_status": "In Review"})
        self.assertIsNone(cost_tracker.record_delivery("NOPE-1", pushed=True))

    def test_legacy_ledger_is_imported_once(self):
        os.makedirs("dev")
        with open(cost_tracker.get_legacy_ledger_path(), "w") as f:
            json.dump([{"date": "2026-01-01 10:00", "ticket": "OLD-1", "summary": "Old", "branch": "feat/OLD-1",
                        "model": "Claude 3.7 Sonnet", "input_tokens": 10, "output_tokens": 5, "total_tokens": 15,
                        "cost_usd": 0.5}], f)
        with patch("tools.cost_tracker.usage_report.collect", return_value=MEASURED):
            cost_tracker.start_ticket("NEW-1")
            cost_tracker.log_ticket_completion("NEW-1", branch="feat/NEW-1", post_jira=False)
        with open(cost_tracker.get_runs_file_path()) as f:
            runs = json.load(f)["runs"]
        self.assertEqual([r["ticket"] for r in runs], ["OLD-1", "NEW-1"])
        self.assertTrue(runs[0]["estimated"])
        self.assertEqual(runs[0]["usage"]["totals"]["total_tokens"], 15)

    def test_jira_comment_says_estimated(self):
        with patch("tools.cost_tracker.usage_report.collect", return_value={"available": False}), \
                patch("tools.cost_tracker.usage_report.detect_model", return_value=None), \
                patch("jira_sync.comment_ticket") as comment:
            cost_tracker.log_ticket_completion("TEST-3", post_jira=True)
        self.assertIn("(estimated)", comment.call_args[0][1])


if __name__ == "__main__":
    unittest.main()
