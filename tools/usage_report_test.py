#!/usr/bin/env python3
"""Unit tests for dev-kit usage report."""
import json
import os
import re
import tempfile
import unittest
from unittest.mock import patch

from tools import usage_report


def assistant(ts, msg_id, model, inp, out, cw=0, cr=0, cw_1h=0, sidechain=False):
    return {
        "type": "assistant",
        "timestamp": ts,
        "isSidechain": sidechain,
        "message": {
            "id": msg_id,
            "model": model,
            "usage": {
                "input_tokens": inp,
                "output_tokens": out,
                "cache_creation_input_tokens": cw,
                "cache_read_input_tokens": cr,
                "cache_creation": {"ephemeral_1h_input_tokens": cw_1h},
            },
        },
    }


def user(text):
    return {"type": "user", "message": {"content": text}}


def write_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


class TestPricing(unittest.TestCase):
    def setUp(self):
        self.table = usage_report.load_pricing("/nonexistent")

    def test_current_models_match_their_own_rates(self):
        cases = {
            "claude-opus-5-5": "Claude Opus 5.5",
            "claude-sonnet-5-5": "Claude Sonnet 5 / 5.5",
            "claude-haiku-5-5": "Claude Haiku 5.5 (prompts up to 100K)",
            "claude-fable-5-1": "Claude Fable 5.1",
            "claude-opus-4-8": "Claude Opus 5 / 4.5-4.8",
            "Gemini 3.8 Flash (Medium)": "Gemini 3.8 Flash (introductory rate until 31/12/2026)",
        }
        for model, label in cases.items():
            self.assertEqual(usage_report.match_pricing(model, self.table)["label"], label, model)

    def test_unknown_model_uses_default(self):
        self.assertEqual(usage_report.match_pricing(None, self.table), self.table["default"])
        self.assertEqual(usage_report.match_pricing("mystery-model", self.table), self.table["default"])

    def test_cost_includes_cache_and_1h_writes(self):
        # Opus 5.5: 1M in $4 + 1M out $20 + 1M 5m write $5 + 1M 1h write $8 + 1M read $0.20
        counts = {"input_tokens": 1_000_000, "output_tokens": 1_000_000,
                  "cache_creation_input_tokens": 2_000_000, "cache_read_input_tokens": 1_000_000}
        cost = usage_report.cost_of(counts, "claude-opus-5-5", self.table, cache_write_1h=1_000_000)
        self.assertAlmostEqual(cost, 37.20, places=4)

    def test_no_legacy_default_model(self):
        with open(usage_report.PRICING_FILE, encoding="utf-8") as f:
            text = f.read()
        self.assertNotRegex(text, re.compile(r"claude[ -]3|3\.7 sonnet", re.I))
        self.assertNotIn("claude", self.table["default"]["label"].lower())

    def test_project_override_is_tried_first(self):
        with tempfile.TemporaryDirectory() as root:
            write = {"models": [{"pattern": "opus-5-5", "label": "Negotiated", "input": 1, "output": 1,
                                 "cache_write": 1, "cache_read": 1}]}
            os.makedirs(os.path.join(root, "dev"))
            with open(os.path.join(root, "dev", "pricing.json"), "w") as f:
                json.dump(write, f)
            table = usage_report.load_pricing(root)
            self.assertEqual(usage_report.match_pricing("claude-opus-5-5", table)["label"], "Negotiated")


class TestClaudeSessions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = os.path.join(self.tmp.name, "claude")
        self.root = os.path.join(self.tmp.name, "project")
        os.makedirs(self.root)
        encoded = re.sub(r"[^A-Za-z0-9-]", "-", os.path.abspath(self.root))
        self.pdir = os.path.join(self.config, "projects", encoded)
        write_jsonl(os.path.join(self.pdir, "s1.jsonl"), [
            user("/dev PAS-1"),
            assistant("2026-10-27T09:00:00Z", "old", "claude-opus-5-5", 999, 999),
            assistant("2026-10-27T10:05:00Z", "m1", "claude-opus-5-5", 100, 50, cw=1000, cr=5000, cw_1h=1000),
            assistant("2026-10-27T10:05:00Z", "m1", "claude-opus-5-5", 100, 50),  # duplicate id
        ])
        write_jsonl(os.path.join(self.pdir, "s1", "subagents", "agent-a.jsonl"), [
            user("dev-kit-agent: backend\nImplement AC-1"),
            assistant("2026-10-27T10:10:00Z", "b1", "claude-sonnet-5-5", 200, 80),
        ])
        write_jsonl(os.path.join(self.pdir, "s1", "subagents", "agent-b.jsonl"), [
            user("dev-kit-agent: qa-verifier\nVerify"),
            assistant("2026-10-27T10:20:00Z", "q1", "claude-opus-5-5", 300, 40),
        ])
        self.env = patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": self.config}, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_measures_since_start_and_attributes_roles(self):
        res = usage_report.collect(self.root, "2026-10-27T10:00:00Z", engine="claude")
        self.assertTrue(res["available"])
        self.assertFalse(res["estimated"])
        agents = {a["agent"]: a for a in res["agents"]}
        self.assertEqual(list(agents), ["orchestrator", "backend", "qa"])
        self.assertEqual(agents["orchestrator"]["input_tokens"], 100)  # old record and duplicate skipped
        self.assertEqual(agents["backend"]["output_tokens"], 80)
        self.assertEqual(res["totals"]["input_tokens"], 600)

    def test_each_model_is_priced_at_its_own_rate(self):
        res = usage_report.collect(self.root, "2026-10-27T10:00:00Z", engine="claude")
        agents = {a["agent"]: a for a in res["agents"]}
        # backend on Sonnet 5.5: 200 * $2 + 80 * $10 per 1M
        self.assertAlmostEqual(agents["backend"]["cost_usd"], round((200 * 2 + 80 * 10) / 1e6, 4))
        self.assertIn("claude-sonnet-5-5", res["models"])
        self.assertAlmostEqual(res["cost_usd"], sum(a["cost_usd"] for a in res["agents"]), places=4)

    def test_no_sessions_reports_unavailable(self):
        with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": os.path.join(self.tmp.name, "none")}):
            res = usage_report.collect(self.root, "2026-10-27T10:00:00Z", engine="claude")
        self.assertFalse(res["available"])


class TestAntigravitySessions(unittest.TestCase):
    def test_reads_transcript_and_subagents(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = os.path.join(tmp, "brain")
            main_id = "11111111-1111-1111-1111-111111111111"
            sub_id = "22222222-2222-2222-2222-222222222222"
            write_jsonl(usage_report.transcript_path(brain, main_id), [
                {"created_at": "2026-10-27T10:00:00Z", "content": "Changed `Model Selection` from None to Gemini 3.8 Flash.\n"},
                {"created_at": "2026-10-27T10:01:00Z", "input_tokens": 1000, "output_tokens": 100, "cache_read_tokens": 500,
                 "tool_calls": [{"name": "invoke_subagent", "args": {"Role": "QA Verifier", "Prompt": "dev-kit-agent: qa\nVerify"}}]},
                {"created_at": "2026-10-27T10:02:00Z", "content": f'{{"conversationId": "{sub_id}"}}'},
            ])
            write_jsonl(usage_report.transcript_path(brain, sub_id), [
                {"created_at": "2026-10-27T10:03:00Z", "input_tokens": 400, "output_tokens": 40},
            ])
            with patch.dict(os.environ, {"ANTIGRAVITY_APP_DATA_DIR": tmp, "ANTIGRAVITY_CONVERSATION_ID": main_id}):
                res = usage_report.collect(tmp, "2026-10-27T09:00:00Z", engine="antigravity")
        self.assertTrue(res["available"])
        agents = {a["agent"]: a for a in res["agents"]}
        self.assertEqual(agents["orchestrator"]["cache_read_input_tokens"], 500)
        self.assertEqual(agents["qa"]["input_tokens"], 400)
        self.assertEqual(res["models"][0], "Gemini 3.8 Flash")


if __name__ == "__main__":
    unittest.main()
