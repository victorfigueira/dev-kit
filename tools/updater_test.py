#!/usr/bin/env python3
"""Unit tests for dev-kit updater tool."""
import unittest
from unittest.mock import patch
import os
import tempfile
from tools.updater import (parse_semver, is_newer, read_local_version, main,
                           changelog_since, check_for_updates, perform_update)


class TestUpdater(unittest.TestCase):
    def test_parse_semver(self):
        self.assertEqual(parse_semver("0.1.0"), (0, 1, 0))
        self.assertEqual(parse_semver("v1.2.3"), (1, 2, 3))
        self.assertEqual(parse_semver("v2.0.0-beta"), (2, 0, 0))
        self.assertEqual(parse_semver("invalid"), (0, 0, 0))

    def test_is_newer(self):
        self.assertTrue(is_newer("0.2.1", "0.2.0"))
        self.assertTrue(is_newer("1.0.0", "0.9.9"))
        self.assertTrue(is_newer("v0.3.0", "0.2.9"))
        self.assertFalse(is_newer("0.2.0", "0.2.0"))
        self.assertFalse(is_newer("0.1.9", "0.2.0"))

    def test_read_local_version(self):
        ver = read_local_version()
        self.assertNotEqual(ver, "0.0.0")
        self.assertTrue(len(ver.split(".")) >= 2)

    def test_changelog_since_returns_only_newer_entries(self):
        text = (
            "# Changelog\n\n"
            "## 0.5.0 – 28/10/2026\n- Ask before updating.\n- Add /dev-check-update.\n\n"
            "## 0.4.8 – 27/10/2026\n- Explicit Jira commands.\n\n"
            "## 0.4.7 – 27/10/2026\n- Model detection.\n"
        )
        entries = changelog_since(text, "0.4.7")
        self.assertEqual([e["version"] for e in entries], ["0.5.0", "0.4.8"])
        self.assertEqual(entries[0]["date"], "28/10/2026")
        self.assertEqual(entries[0]["notes"], ["Ask before updating.", "Add /dev-check-update."])

    def test_changelog_since_handles_missing_changelog(self):
        self.assertEqual(changelog_since(None, "0.4.7"), [])

    @patch("tools.updater.fetch_remote_changelog", return_value="## 1.0.0 – 01/11/2026\n- Breaking.\n")
    @patch("tools.updater.fetch_remote_version", return_value="1.0.0")
    @patch("tools.updater.read_local_version", return_value="0.4.8")
    def test_check_reports_major_change_and_changelog(self, _local, _remote, _changelog):
        status = check_for_updates()
        self.assertTrue(status["update_available"])
        self.assertTrue(status["major_change"])
        self.assertEqual(status["changelog"][0]["version"], "1.0.0")

    @patch("tools.updater.fetch_remote_version", return_value=None)
    @patch("tools.updater.read_local_version", return_value="0.4.8")
    def test_check_offline(self, _local, _remote):
        status = check_for_updates()
        self.assertTrue(status["offline"])
        self.assertFalse(status["update_available"])
        self.assertEqual(status["changelog"], [])

    @patch("tools.updater.subprocess.run")
    @patch("tools.updater.safe_urlopen")
    def test_update_refuses_inside_kit_source_repo(self, mock_urlopen, mock_run):
        with tempfile.TemporaryDirectory() as root:
            for name in ("install.sh", "VERSION"):
                open(os.path.join(root, name), "w").close()
            self.assertFalse(perform_update(target_dir=root))
        mock_urlopen.assert_not_called()
        mock_run.assert_not_called()

    def test_auto_command_is_gone(self):
        with patch("sys.argv", ["updater.py", "auto"]), patch("sys.stderr"):
            with self.assertRaises(SystemExit):
                main()

if __name__ == "__main__":
    unittest.main()
