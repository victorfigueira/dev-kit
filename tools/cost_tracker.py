#!/usr/bin/env python3
"""Token and USD cost tracking for dev-kit.

Measures the tokens a ticket consumed from the local Claude Code or Antigravity session
files (tools/usage_report.py), attributed per squad role, and keeps a cumulative ledger in
dev/COSTS.md and dev/cost_ledger.json. When no session files are found it falls back to an
estimate from the diff size, marked "estimated": true everywhere it is shown.

Usage:
  python3 dev-kit/tools/cost_tracker.py start --ticket TICKET_KEY
  python3 dev-kit/tools/cost_tracker.py report [--since ISO] [--model MODEL] [--json]
  python3 dev-kit/tools/cost_tracker.py log --ticket TICKET_KEY [--summary TITLE] [--branch BRANCH] [--since ISO] [--model MODEL] [--no-jira]
  python3 dev-kit/tools/cost_tracker.py estimate [--base-branch BRANCH] [--model MODEL] [--json]
  python3 dev-kit/tools/cost_tracker.py reset
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usage_report  # noqa: E402


def dev_path(name):
    return os.path.join(os.getcwd(), "dev", name)


def get_session_file_path():
    """dev/session.json holds the ticket key and start time written by `start`."""
    return dev_path("session.json")


def get_ledger_file_path():
    return dev_path("cost_ledger.json")


def get_costs_md_path():
    return dev_path("COSTS.md")


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def start_ticket(ticket_key):
    """Record the ticket start time, so the cost covers only this ticket's session records."""
    data = {"ticket": ticket_key, "since": utc_now()}
    path = get_session_file_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def load_session():
    path = get_session_file_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            pass
    return {}


def detect_active_model(model_override=None, since=None):
    """Model from the override, DEV_KIT_MODEL, or the session files. None when unknown."""
    if model_override:
        return model_override.strip()
    env_model = os.environ.get("DEV_KIT_MODEL")
    if env_model:
        return env_model.strip()
    return usage_report.detect_model(os.getcwd(), since)


def calculate_cost(input_tokens, output_tokens, model=None):
    """USD cost of plain input and output tokens at the model's rate."""
    table = usage_report.load_pricing(os.getcwd())
    cost = usage_report.cost_of({"input_tokens": input_tokens, "output_tokens": output_tokens}, model, table)
    return round(cost, 4)


def estimate_from_diff(base_branch=None, model_override=None):
    """Estimate token usage from the diff and dev/PLAN.md size. Used only without session files."""
    model = detect_active_model(model_override) or "unknown"
    table = usage_report.load_pricing(os.getcwd())
    pricing = usage_report.match_pricing(model, table)

    diff_chars = 4000
    try:
        res = subprocess.run(["git", "diff", base_branch or "main"], capture_output=True, text=True)
        if res.returncode == 0:
            diff_chars = len(res.stdout)
    except OSError:
        pass

    plan_chars = 0
    plan_path = dev_path("PLAN.md")
    if os.path.exists(plan_path):
        with open(plan_path, "r", encoding="utf-8", errors="replace") as f:
            plan_chars = len(f.read())

    # Approximate 4 characters per token
    base_tokens = max(500, diff_chars // 4) + max(400, plan_chars // 4)
    distribution = {
        "pm": (2.5, 0.8),
        "database": (1.5, 0.5),
        "backend": (3.0, 1.2),
        "frontend": (2.8, 1.0),
        "qa": (2.0, 0.4),
    }

    agents = []
    for key, (in_ratio, out_ratio) in distribution.items():
        in_tok = int(base_tokens * in_ratio) + 2500
        out_tok = int(base_tokens * out_ratio) + 600
        agents.append({
            "agent": key,
            "name": usage_report.ROLES[key],
            "runs": 1,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "total_tokens": in_tok + out_tok,
            "cost_usd": calculate_cost(in_tok, out_tok, model),
        })

    totals = {t: sum(a[t] for a in agents) for t in usage_report.TYPES}
    totals["total_tokens"] = sum(totals[t] for t in usage_report.TYPES)
    return {
        "available": True,
        "estimated": True,
        "source": "Estimate from diff and plan size (no session files found)",
        "since": None,
        "models": [model],
        "pricing": {model: pricing["label"]},
        "pricing_as_of": table.get("as_of"),
        "totals": totals,
        "cost_usd": round(sum(a["cost_usd"] for a in agents), 4),
        "agents": agents,
        "notes": "Approximated at 4 characters per token over the diff and dev/PLAN.md.",
    }


def generate_cost_report(since=None, model_override=None, base_branch=None):
    """Measured report from session files since the ticket start, or an estimate."""
    since = since or load_session().get("since")
    if since:
        report = usage_report.collect(os.getcwd(), since)
        if report.get("available"):
            if model_override:
                report["models"] = [model_override]
            return report
    return estimate_from_diff(base_branch, model_override)


def model_label(report):
    return ", ".join(report.get("models") or ["unknown"])


def estimated_tag(report):
    return " (estimated)" if report.get("estimated") else ""


def format_markdown(report):
    """Format the cost report into GitHub-flavored markdown."""
    t = report["totals"]
    md = ["### Development Cost & Token Consumption\n"]
    if report.get("estimated"):
        md.append("> **Estimated:** no session files were found, so these figures are approximated from the diff size.\n")
    md.append(f"- **AI Model:** {model_label(report)}")
    md.append(f"- **Source:** {report['source']}" + (f" since {report['since']}" if report.get("since") else ""))
    md.append(f"- **Total Tokens:** {t['total_tokens']:,} ({t['input_tokens']:,} input · {t['output_tokens']:,} output · "
              f"{t['cache_creation_input_tokens']:,} cache write · {t['cache_read_input_tokens']:,} cache read)")
    md.append(f"- **Total Development Cost:** **${report['cost_usd']:.4f} USD**{estimated_tag(report)}"
              f" (prices as of {report.get('pricing_as_of')})\n")

    md.append("| Squad Role | Runs | Input | Output | Cache Write | Cache Read | Cost (USD) |")
    md.append("|---|---|---|---|---|---|---|")
    for a in report["agents"]:
        md.append(f"| **{a['name']}** | {a['runs']} | {a['input_tokens']:,} | {a['output_tokens']:,} | "
                  f"{a['cache_creation_input_tokens']:,} | {a['cache_read_input_tokens']:,} | ${a['cost_usd']:.4f} |")
    md.append(f"| **Total** | | **{t['input_tokens']:,}** | **{t['output_tokens']:,}** | "
              f"**{t['cache_creation_input_tokens']:,}** | **{t['cache_read_input_tokens']:,}** | "
              f"**${report['cost_usd']:.4f} USD** |\n")
    return "\n".join(md)


def render_costs_markdown(ledger):
    """Render cumulative COSTS.md summary table."""
    total_tokens = sum(e.get("total_tokens", 0) for e in ledger)
    total_cost = sum(e.get("cost_usd", 0.0) for e in ledger)
    estimated = sum(1 for e in ledger if e.get("estimated"))

    lines = [
        "# Project Development Cost & Token Ledger\n",
        "Cumulative token consumption and expenditure tracked across all resolved tickets in `dev-kit`.\n",
        f"- **Total Tickets Resolved:** {len(ledger)}" + (f" ({estimated} estimated)" if estimated else ""),
        f"- **Total Tokens Consumed:** {total_tokens:,}",
        f"- **Grand Total Expenditure:** **${total_cost:.4f} USD**\n",
        "| Date | Ticket | Summary | Model | Tokens | Cost (USD) | Source | Branch |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for e in ledger:
        source = "estimated" if e.get("estimated") else "measured"
        lines.append(
            f"| {e['date']} | **{e['ticket']}** | {e.get('summary', '')} | {e.get('model', '')} | "
            f"{e.get('total_tokens', 0):,} | ${e.get('cost_usd', 0.0):.4f} | {source} | `{e.get('branch', '')}` |"
        )
    ticket_label = f"{len(ledger)} ticket{'s' if len(ledger) != 1 else ''} completed"
    lines.append(f"| **TOTAL** | | **{ticket_label}** | | **{total_tokens:,}** | **${total_cost:.4f} USD** | | |\n")

    md_path = get_costs_md_path()
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def log_ticket_completion(ticket_key, summary=None, branch=None, since=None, model_override=None, post_jira=True):
    """Log a completed ticket to dev/cost_ledger.json, dev/COSTS.md and, optionally, Jira."""
    report = generate_cost_report(since, model_override)
    ledger_path = get_ledger_file_path()

    ledger = []
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
        except (OSError, ValueError):
            ledger = []

    t = report["totals"]
    entry = {
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ticket": ticket_key,
        "summary": summary or f"Task {ticket_key}",
        "branch": branch or f"feat/{ticket_key}",
        "model": model_label(report),
        "since": report.get("since"),
        "estimated": bool(report.get("estimated")),
        "input_tokens": t["input_tokens"],
        "output_tokens": t["output_tokens"],
        "cache_creation_input_tokens": t["cache_creation_input_tokens"],
        "cache_read_input_tokens": t["cache_read_input_tokens"],
        "total_tokens": t["total_tokens"],
        "cost_usd": report["cost_usd"],
        "roles": {a["agent"]: {"tokens": a["total_tokens"], "cost_usd": a["cost_usd"]} for a in report["agents"]},
    }

    ledger = [e for e in ledger if e.get("ticket") != ticket_key] + [entry]
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)
    render_costs_markdown(ledger)

    if post_jira:
        try:
            from jira_sync import comment_ticket
            comment_ticket(ticket_key, (
                f"✅ Squad development complete · Quality Gate: APPROVED\n"
                f"• Branch: {entry['branch']}\n"
                f"• Tokens: {entry['total_tokens']:,}\n"
                f"• Development Cost: ${entry['cost_usd']:.4f} USD{estimated_tag(report)} ({entry['model']})"
            ))
        except Exception as e:
            print(f"Note: Could not post comment to Jira: {e}", file=sys.stderr)

    reset_session(quiet=True)
    return entry


def reset_session(quiet=False):
    """Remove dev/session.json (the ticket start time)."""
    path = get_session_file_path()
    if os.path.exists(path):
        os.remove(path)
    if not quiet:
        print("✅ Session start time reset.")


def main():
    parser = argparse.ArgumentParser(description="dev-kit token and USD cost tracking.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_p = subparsers.add_parser("start", help="Record the ticket start time in dev/session.json")
    start_p.add_argument("--ticket", required=True, help="Jira ticket key (e.g. PAS-1)")

    rep_p = subparsers.add_parser("report", help="Report tokens and cost since the ticket start")
    rep_p.add_argument("--since", default=None, help="Start time, ISO 8601 UTC (default: dev/session.json)")
    rep_p.add_argument("--model", default=None, help="Model override")
    rep_p.add_argument("--json", action="store_true", help="Output JSON format")

    log_p = subparsers.add_parser("log", help="Log ticket completion to the cumulative ledger")
    log_p.add_argument("--ticket", required=True, help="Jira ticket key (e.g. PAS-1)")
    log_p.add_argument("--summary", default=None, help="Ticket summary/title")
    log_p.add_argument("--branch", default=None, help="Git branch name")
    log_p.add_argument("--since", default=None, help="Start time, ISO 8601 UTC (default: dev/session.json)")
    log_p.add_argument("--model", default=None, help="Model override")
    log_p.add_argument("--no-jira", action="store_true", help="Do not post Jira comment")

    est_p = subparsers.add_parser("estimate", help="Estimate cost from git diff and artifacts")
    est_p.add_argument("--base-branch", default="main", help="Base branch for diff comparison")
    est_p.add_argument("--model", default=None, help="Model override")
    est_p.add_argument("--json", action="store_true", help="Output JSON format")

    subparsers.add_parser("reset", help="Remove the recorded ticket start time")

    args = parser.parse_args()

    if args.command == "start":
        data = start_ticket(args.ticket)
        print(f"✅ {data['ticket']} started at {data['since']}")
    elif args.command in ("report", "estimate"):
        if args.command == "report":
            report = generate_cost_report(args.since, args.model)
        else:
            report = estimate_from_diff(args.base_branch, args.model)
        print(json.dumps(report, indent=2) if args.json else format_markdown(report))
    elif args.command == "log":
        entry = log_ticket_completion(args.ticket, args.summary, args.branch, args.since, args.model, not args.no_jira)
        tag = " · estimated" if entry["estimated"] else ""
        print(f"✅ Logged {entry['ticket']} (${entry['cost_usd']:.4f} USD · {entry['total_tokens']:,} tokens{tag}) "
              f"to dev/COSTS.md and dev/cost_ledger.json")
    elif args.command == "reset":
        reset_session()
    return 0


if __name__ == "__main__":
    sys.exit(main())
