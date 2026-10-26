#!/usr/bin/env python3
"""Unit tests for dev-kit universal test runner."""
import os
import tempfile
import unittest
from tools.test_runner import parse_context_file, detect_test_commands, run_command


class TestTestRunner(unittest.TestCase):
    def test_parse_context_file(self):
        content = """
## 2. Testing & Verification Commands
- **Unit & Integration Tests:** `npm test`
- **Type Checking:** `npm run typecheck`
- **Linting & Code Style:** `npm run lint`
"""
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".md") as f:
            f.write(content)
            temp_path = f.name

        try:
            res = parse_context_file(temp_path)
            self.assertEqual(res.get("test"), "npm test")
            self.assertEqual(res.get("typecheck"), "npm run typecheck")
            self.assertEqual(res.get("lint"), "npm run lint")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_run_command_success(self):
        res = run_command("echo 'hello world'")
        self.assertEqual(res["status"], "passed")
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("hello world", res["stdout"])

    def test_run_command_failure(self):
        res = run_command("false")
        self.assertEqual(res["status"], "failed")
        self.assertNotEqual(res["exit_code"], 0)


if __name__ == "__main__":
    unittest.main()
