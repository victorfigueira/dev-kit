#!/usr/bin/env python3
"""Jira Synchronization & Task Ingestion Tool for dev-kit.

Connects to Jira Cloud via REST API using standard environment variables:
  - JIRA_BASE_URL (e.g. https://company.atlassian.net)
  - JIRA_USER_EMAIL (e.g. user@company.com)
  - JIRA_API_TOKEN (Atlassian API token)

Usage:
  python3 dev-kit/tools/jira_sync.py fetch <TICKET_KEY> [--json]
  python3 dev-kit/tools/jira_sync.py backlog [PROJECT_KEY] [--limit N] [--json]
  python3 dev-kit/tools/jira_sync.py next [PROJECT_KEY] [--json]
  python3 dev-kit/tools/jira_sync.py transition <TICKET_KEY> <STATUS_NAME_OR_ID>
  python3 dev-kit/tools/jira_sync.py comment <TICKET_KEY> <COMMENT_TEXT>
"""
import argparse
import base64
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request


def safe_urlopen(req, timeout=15):
    """Execute urllib request with fallback for environments with SSL certificate verification issues."""
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e) or "certificate verify failed" in str(e).lower():
            ctx = ssl._create_unverified_context()
            return urllib.request.urlopen(req, timeout=timeout, context=ctx)
        raise


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


def extract_adf_text(node):
    """Recursively extract plain text from Atlassian Document Format (ADF) nodes."""
    if not isinstance(node, dict):
        return ""
    text = node.get("text", "")
    for child in node.get("content", []):
        child_text = extract_adf_text(child)
        if child_text:
            text = f"{text}\n{child_text}" if text else child_text
    return text.strip()


def parse_description(desc_raw):
    """Parse description whether it is plain text or an ADF structure."""
    if isinstance(desc_raw, str):
        return desc_raw
    elif isinstance(desc_raw, dict):
        return extract_adf_text(desc_raw)
    return ""


def load_env_credentials():
    """Resolve JIRA credentials from environment, .env files, or MCP configs."""
    base_url = os.environ.get("JIRA_BASE_URL")
    email = os.environ.get("JIRA_USER_EMAIL") or os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_API_TOKEN")

    if base_url and email and token:
        return base_url, email, token

    # 1. Check local .env files
    env_paths = [".env", ".env.local", "dev/.env", os.path.expanduser("~/.jira.env")]
    for env_path in env_paths:
        if base_url and email and token:
            break
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("\"'")
                        if k == "JIRA_BASE_URL" and not base_url:
                            base_url = v
                        elif k in ("JIRA_USER_EMAIL", "JIRA_EMAIL") and not email:
                            email = v
                        elif k == "JIRA_API_TOKEN" and not token:
                            token = v
            except Exception:
                pass

    # 2. Check MCP configurations (Antigravity, Cursor, Claude)
    mcp_paths = [
        os.path.expanduser("~/.gemini/antigravity/mcp_config.json"),
        os.path.expanduser("~/.cursor/mcp.json"),
        os.path.expanduser("~/.claude/mcp.json"),
    ]
    for mcp_path in mcp_paths:
        if base_url and email and token:
            break
        if os.path.exists(mcp_path):
            try:
                with open(mcp_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    jira_cfg = data.get("mcpServers", {}).get("jira", {})
                    jira_env = jira_cfg.get("env", {})
                    if not base_url and jira_env.get("JIRA_BASE_URL"):
                        base_url = jira_env.get("JIRA_BASE_URL")
                    if not email and (jira_env.get("JIRA_EMAIL") or jira_env.get("JIRA_USER_EMAIL")):
                        email = jira_env.get("JIRA_EMAIL") or jira_env.get("JIRA_USER_EMAIL")
                    if not token and jira_env.get("JIRA_API_TOKEN"):
                        token = jira_env.get("JIRA_API_TOKEN")
            except Exception:
                pass

    return base_url, email, token


def get_auth_header():
    base_url, email, token = load_env_credentials()

    if not base_url or not email or not token:
        return None, None

    credentials = f"{email}:{token}".encode("utf-8")
    auth_header = f"Basic {base64.b64encode(credentials).decode('utf-8')}"
    return base_url.rstrip("/"), {"Authorization": auth_header, "Content-Type": "application/json"}


def detect_project_key(provided_key=None):
    """Resolve project key from argument, dev/project-context.md, or environment."""
    if provided_key:
        return provided_key.strip().upper()

    env_key = os.environ.get("JIRA_PROJECT_KEY")
    if env_key:
        return env_key.strip().upper()

    # Try reading from dev/project-context.md or dev-kit/templates/project-context.md
    context_paths = ["dev/project-context.md", "dev-kit/templates/project-context.md"]
    for path in context_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Match patterns like: jira.project_key: PAS or Project key PAS
                    match = re.search(r"(?:project_key|Project key)[:\s]+([A-Z0-9]+)", content, re.IGNORECASE)
                    if match:
                        return match.group(1).upper()
            except Exception:
                pass

    return "DEV"


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
            "priority": "Medium",
            "acceptance_criteria": [
                "Implement required functionality",
                "Write unit tests",
                "Verify test suite passes"
            ],
            "offline": True
        }

    url = f"{base_url}/rest/api/3/issue/{ticket_key}?fields=summary,description,issuetype,status,priority"
    req = urllib.request.Request(url, headers=headers)
    try:
        with safe_urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            fields = data.get("fields", {})
            desc_text = parse_description(fields.get("description"))
            acs = extract_acceptance_criteria(desc_text)
            return {
                "key": ticket_key,
                "summary": fields.get("summary", ""),
                "description": desc_text,
                "type": fields.get("issuetype", {}).get("name", "Task"),
                "status": fields.get("status", {}).get("name", "Unknown"),
                "priority": fields.get("priority", {}).get("name", "Medium"),
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
            "priority": "Medium",
            "acceptance_criteria": [],
            "error": str(e)
        }


def fetch_backlog(project_key=None, limit=10):
    """Fetch active and prioritized sprint/backlog tickets for the given project."""
    pkey = detect_project_key(project_key)
    base_url, headers = get_auth_header()

    if not base_url:
        # Structured offline backlog mock
        return [
            {
                "key": f"{pkey}-101",
                "summary": f"Setup core infrastructure and schema models for {pkey}",
                "description": "- [ ] Define models\n- [ ] Implement initial migrations\n- [ ] Run test suite",
                "type": "Task",
                "status": "In Progress",
                "priority": "High",
                "acceptance_criteria": [
                    "Define models",
                    "Implement initial migrations",
                    "Run test suite"
                ],
                "offline": True
            },
            {
                "key": f"{pkey}-102",
                "summary": f"Implement domain business logic and API endpoints for {pkey}",
                "description": "- [ ] Add input validation schemas\n- [ ] Decouple service layers\n- [ ] Add unit tests",
                "type": "Task",
                "status": "To Do",
                "priority": "Medium",
                "acceptance_criteria": [
                    "Add input validation schemas",
                    "Decouple service layers",
                    "Add unit tests"
                ],
                "offline": True
            },
            {
                "key": f"{pkey}-103",
                "summary": f"Build user interface components and state handling for {pkey}",
                "description": "- [ ] Implement 4 async UI states\n- [ ] Add keyboard navigation and a11y\n- [ ] Verify responsive layout",
                "type": "Task",
                "status": "To Do",
                "priority": "Low",
                "acceptance_criteria": [
                    "Implement 4 async UI states",
                    "Add keyboard navigation and a11y",
                    "Verify responsive layout"
                ],
                "offline": True
            }
        ][:limit]

    jql = f'project = "{pkey}" AND statusCategory in ("To Do", "In Progress") ORDER BY rank ASC, priority DESC, created ASC'
    query_str = urllib.parse.urlencode({
        "jql": jql,
        "maxResults": limit,
        "fields": "summary,description,issuetype,status,priority"
    })
    url = f"{base_url}/rest/api/3/search?{query_str}"
    req = urllib.request.Request(url, headers=headers)

    try:
        with safe_urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            issues = data.get("issues", [])
            results = []
            for issue in issues:
                fields = issue.get("fields", {})
                desc_text = parse_description(fields.get("description"))
                acs = extract_acceptance_criteria(desc_text)
                results.append({
                    "key": issue.get("key"),
                    "summary": fields.get("summary", ""),
                    "description": desc_text,
                    "type": fields.get("issuetype", {}).get("name", "Task"),
                    "status": fields.get("status", {}).get("name", "Unknown"),
                    "priority": fields.get("priority", {}).get("name", "Medium"),
                    "acceptance_criteria": acs,
                    "offline": False
                })
            return results
    except Exception as e:
        print(f"Error fetching Jira backlog: {e}", file=sys.stderr)
        return []


def fetch_next_ticket(project_key=None):
    """Retrieve the single top-priority pending ticket from the project backlog."""
    backlog = fetch_backlog(project_key=project_key, limit=1)
    if backlog:
        return backlog[0]
    return None


def transition_ticket(ticket_key, target_status):
    """Transition Jira ticket status."""
    base_url, headers = get_auth_header()
    if not base_url:
        print(f"Offline mode: simulated transition of {ticket_key} to '{target_status}'.")
        return True

    # 1. Fetch available transitions
    trans_url = f"{base_url}/rest/api/3/issue/{ticket_key}/transitions"
    req = urllib.request.Request(trans_url, headers=headers)
    try:
        with safe_urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            transitions = data.get("transitions", [])
            matched_id = None
            for t in transitions:
                if t.get("name", "").lower() == target_status.lower() or t.get("id") == str(target_status):
                    matched_id = t.get("id")
                    break

            if not matched_id:
                available = ", ".join([f"'{t.get('name')}' (id: {t.get('id')})" for t in transitions])
                print(f"Transition '{target_status}' not found for {ticket_key}. Available: {available}", file=sys.stderr)
                return False

            # 2. Perform transition
            post_data = json.dumps({"transition": {"id": matched_id}}).encode("utf-8")
            post_req = urllib.request.Request(trans_url, data=post_data, headers=headers, method="POST")
            with safe_urlopen(post_req, timeout=15):
                print(f"✅ Successfully transitioned {ticket_key} to '{target_status}'.")
                return True
    except Exception as e:
        print(f"Error transitioning ticket in Jira: {e}", file=sys.stderr)
        return False


def comment_ticket(ticket_key, comment_text):
    """Add a structured markdown comment to a Jira ticket."""
    base_url, headers = get_auth_header()
    if not base_url:
        print(f"⚠️ Jira credentials not configured (checked env vars, .env, and MCP config). Simulated comment on {ticket_key}: {comment_text}")
        return True

    url = f"{base_url}/rest/api/3/issue/{ticket_key}/comment"
    paragraphs = []
    for line in comment_text.splitlines():
        if not line.strip():
            continue
        paragraphs.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": line}]
        })
    if not paragraphs:
        paragraphs = [{"type": "paragraph", "content": [{"type": "text", "text": comment_text}]}]

    body_data = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": paragraphs
        }
    }
    req = urllib.request.Request(url, data=json.dumps(body_data).encode("utf-8"), headers=headers, method="POST")
    try:
        with safe_urlopen(req, timeout=15):
            print(f"✅ Comment added to Jira ticket {ticket_key}.")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
        print(f"Error posting comment to Jira ({e.code}): {error_body}", file=sys.stderr)
        return False
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

    # Backlog
    backlog_p = subparsers.add_parser("backlog", help="Fetch active/pending backlog tickets for project")
    backlog_p.add_argument("project_key", nargs="?", default=None, help="Jira project key (e.g. PAS)")
    backlog_p.add_argument("--limit", type=int, default=10, help="Max tickets to fetch")
    backlog_p.add_argument("--json", action="store_true", help="Output JSON format")

    # Next
    next_p = subparsers.add_parser("next", help="Fetch next prioritized ticket ready for development")
    next_p.add_argument("project_key", nargs="?", default=None, help="Jira project key (e.g. PAS)")
    next_p.add_argument("--json", action="store_true", help="Output JSON format")

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
            print(f"   Type: {ticket['type']} | Status: {ticket['status']} | Priority: {ticket.get('priority', 'Medium')}")
            print("\nAcceptance Criteria:")
            if ticket["acceptance_criteria"]:
                for ac in ticket["acceptance_criteria"]:
                    print(f"   [ ] {ac}")
            else:
                print("   (No explicit checkbox criteria found in description)")
            print()
        return 0

    elif args.command == "backlog":
        tickets = fetch_backlog(args.project_key, limit=args.limit)
        if args.json:
            print(json.dumps(tickets, indent=2))
        else:
            pkey = detect_project_key(args.project_key)
            print(f"\n📋 Jira Backlog for Project [{pkey}] ({len(tickets)} tickets):")
            for idx, t in enumerate(tickets, 1):
                print(f"   {idx}. {t['key']} · {t['summary']} [{t['status']} · {t['priority']}]")
            print()
        return 0

    elif args.command == "next":
        ticket = fetch_next_ticket(args.project_key)
        if not ticket:
            print("No pending tickets found in backlog.")
            return 1
        if args.json:
            print(json.dumps(ticket, indent=2))
        else:
            print(f"\n🎯 Next Prioritized Ticket: {ticket['key']} · {ticket['summary']}")
            print(f"   Status: {ticket['status']} | Priority: {ticket['priority']}")
            print("\nAcceptance Criteria:")
            for ac in ticket.get("acceptance_criteria", []):
                print(f"   [ ] {ac}")
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
