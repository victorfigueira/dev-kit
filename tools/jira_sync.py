#!/usr/bin/env python3
"""Jira Synchronization & Task Ingestion Tool for dev-kit.

Connects to Jira Cloud via REST API using standard environment variables:
  - JIRA_BASE_URL (e.g. https://company.atlassian.net)
  - JIRA_USER_EMAIL (e.g. user@company.com)
  - JIRA_API_TOKEN (Atlassian API token)

Usage:
  python3 dev-kit/tools/jira_sync.py fetch <TICKET_KEY> [--json]
  python3 dev-kit/tools/jira_sync.py transition <TICKET_KEY> <STATUS_NAME_OR_ID>
  python3 dev-kit/tools/jira_sync.py comment <TICKET_KEY> <COMMENT_TEXT>
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request


def extract_acceptance_criteria(description):
    """Parse checkboxes or acceptance criteria lists from Jira description text."""
    if not description:
        return []
    criteria = []
    lines = description.splitlines()
    for line in lines:
        cleaned = line.strip()
        # Markdown checkboxes: - [ ] or - [x]
        cb_match = re.match(r"^[-*]?\s*\[[ xX]\]\s*(.+)$", cleaned)
        if cb_match:
            criteria.append(cb_match.group(1).strip())
            continue
        # Numbered ACs: AC-1: ..., 1. ...
        ac_match = re.match(r"^(?:AC-?\d+:?|\d+\.)\s*(.+)$", cleaned, re.IGNORECASE)
        if ac_match:
            criteria.append(ac_match.group(1).strip())
    return criteria


def get_auth_header():
    base_url = os.environ.get("JIRA_BASE_URL")
    email = os.environ.get("JIRA_USER_EMAIL")
    token = os.environ.get("JIRA_API_TOKEN")

    if not base_url or not email or not token:
        return None, None

    credentials = f"{email}:{token}".encode("utf-8")
    auth_header = f"Basic {base64.b64encode(credentials).decode('utf-8')}"
    return base_url.rstrip("/"), {"Authorization": auth_header, "Content-Type": "application/json"}


def fetch_ticket(ticket_key):
    """Fetch ticket details from Jira or return mock payload if offline."""
    base_url, headers = get_auth_header()
    if not base_url:
        # Offline mock for development and standalone runs
        return {
            "key": ticket_key,
            "summary": f"Task {ticket_key}",
            "description": "- [ ] Implement required functionality\n- [ ] Write unit tests\n- [ ] Verify test suite passes",
            "type": "Task",
            "status": "To Do",
            "acceptance_criteria": [
                "Implement required functionality",
                "Write unit tests",
                "Verify test suite passes"
            ],
            "offline": True
        }

    url = f"{base_url}/rest/api/3/issue/{ticket_key}?fields=summary,description,issuetype,status"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            fields = data.get("fields", {})
            desc_raw = fields.get("description")
            # Extract plain text if ADF (Atlassian Document Format)
            desc_text = ""
            if isinstance(desc_raw, str):
                desc_text = desc_raw
            elif isinstance(desc_raw, dict):
                # Simple extraction of text blocks from ADF
                def extract_adf_text(node):
                    t = node.get("text", "")
                    for child in node.get("content", []):
                        t += "\n" + extract_adf_text(child)
                    return t
                desc_text = extract_adf_text(desc_raw).strip()

            acs = extract_acceptance_criteria(desc_text)
            return {
                "key": ticket_key,
                "summary": fields.get("summary", ""),
                "description": desc_text,
                "type": fields.get("issuetype", {}).get("name", "Task"),
                "status": fields.get("status", {}).get("name", "Unknown"),
                "acceptance_criteria": acs,
                "offline": False
            }
    except Exception as e:
        print(f"Error connecting to Jira API: {e}", file=sys.stderr)
        return {
            "key": ticket_key,
            "summary": f"Task {ticket_key}",
            "description": "",
            "type": "Task",
            "status": "Unknown",
            "acceptance_criteria": [],
            "error": str(e)
        }


def transition_ticket(ticket_key, target_status):
    """Transition Jira ticket status."""
    base_url, headers = get_auth_header()
    if not base_url:
        print(f"ℹ️  [Offline mode] Ticket {ticket_key} transition to '{target_status}' recorded.")
        return True

    # 1. Fetch available transitions
    trans_url = f"{base_url}/rest/api/3/issue/{ticket_key}/transitions"
    req = urllib.request.Request(trans_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            trans_data = json.loads(resp.read().decode("utf-8"))
            transitions = trans_data.get("transitions", [])
            matched_id = None
            for t in transitions:
                if t.get("name", "").lower() == target_status.lower() or t.get("id") == target_status:
                    matched_id = t.get("id")
                    break

            if not matched_id:
                available = [t.get("name") for t in transitions]
                print(f"Error: Transition '{target_status}' not found. Available: {available}", file=sys.stderr)
                return False

            # 2. Execute transition
            body = json.dumps({"transition": {"id": matched_id}}).encode("utf-8")
            post_req = urllib.request.Request(trans_url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(post_req, timeout=15):
                print(f"✅ Ticket {ticket_key} successfully transitioned to '{target_status}'.")
                return True
    except Exception as e:
        print(f"Error executing Jira transition: {e}", file=sys.stderr)
        return False


def comment_ticket(ticket_key, comment_text):
    """Add a comment to Jira ticket."""
    base_url, headers = get_auth_header()
    if not base_url:
        print(f"ℹ️  [Offline mode] Comment for {ticket_key} recorded:\n{comment_text}")
        return True

    url = f"{base_url}/rest/api/3/issue/{ticket_key}/comment"
    # ADF formatted body
    body_data = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": comment_text}]
                }
            ]
        }
    }
    req = urllib.request.Request(url, data=json.dumps(body_data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15):
            print(f"✅ Comment added to {ticket_key}.")
            return True
    except Exception as e:
        print(f"Error posting comment to Jira: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Jira ticket synchronization for dev-kit.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Fetch
    fetch_p = subparsers.add_parser("fetch", help="Fetch ticket details and acceptance criteria")
    fetch_p.add_argument("ticket_key", help="Jira ticket key (e.g. AK-101)")
    fetch_p.add_argument("--json", action="store_true", help="Output JSON format")

    # Transition
    trans_p = subparsers.add_parser("transition", help="Transition ticket status")
    trans_p.add_argument("ticket_key", help="Jira ticket key (e.g. AK-101)")
    trans_p.add_argument("status", help="Target status name or ID (e.g. 'In Progress', 'In Review')")

    # Comment
    comm_p = subparsers.add_parser("comment", help="Add comment to ticket")
    comm_p.add_argument("ticket_key", help="Jira ticket key")
    comm_p.add_argument("text", help="Comment text")

    args = parser.parse_args()

    if args.command == "fetch":
        ticket = fetch_ticket(args.ticket_key)
        if args.json:
            print(json.dumps(ticket, indent=2))
        else:
            print(f"\n📋 Jira Ticket: {ticket['key']} · {ticket['summary']}")
            print(f"   Type: {ticket['type']} | Status: {ticket['status']}")
            print("\nAcceptance Criteria:")
            if ticket["acceptance_criteria"]:
                for ac in ticket["acceptance_criteria"]:
                    print(f"   [ ] {ac}")
            else:
                print("   (No explicit checkbox criteria found in description)")
            print()
        return 0

    elif args.command == "transition":
        success = transition_ticket(args.ticket_key, args.status)
        return 0 if success else 1

    elif args.command == "comment":
        success = comment_ticket(args.ticket_key, args.text)
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
