#!/usr/bin/env python3
"""Unit tests for dev-kit Jira synchronization tool."""
import unittest
from tools.jira_sync import (
    extract_acceptance_criteria,
    fetch_ticket,
    fetch_backlog,
    fetch_next_ticket,
    detect_project_key
)


class TestJiraSync(unittest.TestCase):
    def test_extract_acceptance_criteria_checkboxes(self):
        desc = """
Here is the user story:
- [ ] User can click the favorite button
- [x] Database stores the like in user_favorite_comments
- [ ] Count increments in UI
"""
        acs = extract_acceptance_criteria(desc)
        self.assertEqual(len(acs), 3)
        self.assertEqual(acs[0], "User can click the favorite button")
        self.assertEqual(acs[1], "Database stores the like in user_favorite_comments")
        self.assertEqual(acs[2], "Count increments in UI")

    def test_extract_acceptance_criteria_numbered(self):
        desc = """
AC-1: Endpoint returns 201 Created on success
AC-2: Returns 400 Bad Request on invalid comment ID
"""
        acs = extract_acceptance_criteria(desc)
        self.assertEqual(len(acs), 2)
        self.assertIn("Endpoint returns 201 Created on success", acs)

    def test_offline_fetch_ticket(self):
        ticket = fetch_ticket("AK-101")
        self.assertEqual(ticket["key"], "AK-101")
        self.assertTrue(ticket.get("offline"))
        self.assertTrue(len(ticket["acceptance_criteria"]) > 0)

    def test_offline_fetch_backlog(self):
        backlog = fetch_backlog("PAS", limit=3)
        self.assertEqual(len(backlog), 3)
        self.assertEqual(backlog[0]["key"], "PAS-101")
        self.assertEqual(backlog[0]["status"], "In Progress")
        self.assertEqual(backlog[1]["key"], "PAS-102")

    def test_offline_fetch_next_ticket(self):
        ticket = fetch_next_ticket("PAS")
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket["key"], "PAS-101")
        self.assertEqual(ticket["priority"], "High")

    def test_detect_project_key_provided(self):
        self.assertEqual(detect_project_key("abc"), "ABC")

    def test_load_env_credentials_from_mcp_or_env(self):
        from tools.jira_sync import load_env_credentials
        from unittest.mock import patch
        with patch.dict("os.environ", {"JIRA_BASE_URL": "https://test.atlassian.net", "JIRA_EMAIL": "test@test.com", "JIRA_API_TOKEN": "token123"}):
            url, email, token = load_env_credentials()
            self.assertEqual(url, "https://test.atlassian.net")
            self.assertEqual(email, "test@test.com")
            self.assertEqual(token, "token123")


if __name__ == "__main__":
    unittest.main()
