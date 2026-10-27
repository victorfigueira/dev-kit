#!/usr/bin/env python3
"""Unit tests for dev-kit updater tool."""
import unittest
from unittest.mock import patch
from tools.updater import parse_semver, is_newer, read_local_version, main


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

    @patch("tools.updater.perform_update")
    @patch("tools.updater.check_for_updates")
    def test_auto_updates_when_available(self, mock_check, mock_perform):
        mock_check.return_value = {
            "current_version": "0.4.0",
            "latest_version": "0.4.1",
            "update_available": True,
        }
        mock_perform.return_value = True

        with patch("sys.argv", ["updater.py", "auto"]):
            exit_code = main()
            self.assertEqual(exit_code, 0)
            mock_perform.assert_called_once()

    @patch("tools.updater.perform_update")
    @patch("tools.updater.check_for_updates")
    def test_auto_skips_when_no_update(self, mock_check, mock_perform):
        mock_check.return_value = {
            "current_version": "0.4.1",
            "latest_version": "0.4.1",
            "update_available": False,
        }

        with patch("sys.argv", ["updater.py", "auto"]):
            exit_code = main()
            self.assertEqual(exit_code, 0)
            mock_perform.assert_not_called()


if __name__ == "__main__":
    unittest.main()
