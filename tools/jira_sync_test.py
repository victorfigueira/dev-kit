#!/usr/bin/env python3
"""Unit tests for dev-kit Jira synchronization tool."""
import unittest
from tools.jira_sync import extract_acceptance_criteria, fetch_ticket


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


if __name__ == "__main__":
    unittest.main()
