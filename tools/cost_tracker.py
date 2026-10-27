#!/usr/bin/env python3
"""Token and USD cost tracking and the run record for dev-kit.

Measures the tokens a ticket consumed from the local Claude Code or Antigravity session
files (tools/usage_report.py), attributed per squad role, and records each delivered ticket
in dev/runs.json (schema in RUN.md, "The run record"). dev/COSTS.md is generated from it.
When no session files are found the cost falls back to an estimate from the diff size,
marked "estimated": true everywhere it is shown.

Usage:
  python3 dev-kit/tools/cost_tracker.py start --ticket TICKET_KEY
  python3 dev-kit/tools/cost_tracker.py report [--since ISO] [--model MODEL] [--json]
  python3 dev-kit/tools/cost_tracker.py log --ticket TICKET_KEY --summary TITLE --branch BRANCH
      [--base-branch BRANCH] [--qa-rounds N] [--ac VERIFIED/TOTAL] [--tool TOOL] [--model MODEL] [--since ISO] [--no-jira]
  python3 dev-kit/tools/cost_tracker.py deliver --ticket TICKET_KEY [--pushed] [--jira-status STATUS]
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


def get_runs_file_path():
    """dev/runs.json: one record per delivered ticket, the source of dev/COSTS.md."""
    return dev_path("runs.json")


def get_legacy_ledger_path():
    """dev/cost_ledger.json from dev-kit 0.9 and earlier, imported once into dev/runs.json."""
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



RUNS_SCHEMA_VERSION = 1
KIT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def kit_version():
    try:
        with open(os.path.join(KIT_DIR, "VERSION"), encoding="utf-8") as f:
            return f.read().strip() or "unknown"
    except OSError:
        return "unknown"


def git_value(*args):
    try:
        res = subprocess.run(["git", *args], capture_output=True, text=True)
        return res.stdout.strip() or "unknown" if res.returncode == 0 else "unknown"
    except OSError:
        return "unknown"


def detect_tool(override=None, report=None):
    """Tool running the squad: override, environment, or the session files the usage came from."""
    if override:
        return override
    if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        return "Claude Code"
    if os.environ.get("ANTIGRAVITY_AGENT") or os.environ.get("ANTIGRAVITY_CONVERSATION_ID"):
        return "Antigravity"
    source = (report or {}).get("source", "")
    if source.startswith("Claude Code"):
        return "Claude Code"
    if source.startswith("Antigravity"):
        return "Antigravity"
    return "unknown"


def parse_ac(value):
    """'3/4' -> {"verified": 3, "total": 4}; None when not given or malformed."""
    try:
        verified, total = (int(x) for x in str(value).split("/"))
        return {"verified": verified, "total": total}
    except (TypeError, ValueError):
        return None


def migrate_legacy_ledger():
    """Turn dev/cost_ledger.json entries into run records. Pre-0.9 costs were always estimates."""
    path = get_legacy_ledger_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            ledger = json.load(f)
    except (OSError, ValueError):
        return []
    runs = []
    for e in ledger:
        runs.append({
            "ticket": e.get("ticket"),
            "summary": e.get("summary", ""),
            "branch": e.get("branch", ""),
            "base_branch": "unknown",
            "commit": "unknown",
            "kit_version": "unknown",
            "tool": "unknown",
            "model": e.get("model", "unknown"),
            "started_at": e.get("since"),
            "finished_at": e.get("date"),
            "qa": {"verdict": "APPROVED", "rounds": None, "acceptance_criteria": None},
            "estimated": e.get("estimated", True),
            "cost_usd": e.get("cost_usd", 0.0),
            "usage": {
                "totals": {
                    "input_tokens": e.get("input_tokens", 0),
                    "output_tokens": e.get("output_tokens", 0),
                    "cache_creation_input_tokens": e.get("cache_creation_input_tokens", 0),
                    "cache_read_input_tokens": e.get("cache_read_input_tokens", 0),
                    "total_tokens": e.get("total_tokens", 0),
                },
                "agents": [],
            },
            "delivery": {"pushed": None, "jira_status": None},
            "migrated_from": "cost_ledger.json",
        })
    return runs


def load_runs():
    """Load dev/runs.json, importing dev/cost_ledger.json the first time."""
    path = get_runs_file_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("runs"), list):
                return data
        except (OSError, ValueError):
            pass
    return {"schema_version": RUNS_SCHEMA_VERSION, "runs": migrate_legacy_ledger()}


def save_runs(data):
    path = get_runs_file_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    render_costs_markdown(data["runs"])


def render_costs_markdown(runs):
    """Render dev/COSTS.md from the run records."""
    tokens = [r.get("usage", {}).get("totals", {}).get("total_tokens", 0) for r in runs]
    total_cost = sum(r.get("cost_usd", 0.0) for r in runs)
    estimated = sum(1 for r in runs if r.get("estimated"))

    lines = [
        "# Project Development Cost & Token Ledger\n",
        "Generated from `dev/runs.json` by `dev-kit/tools/cost_tracker.py`. Do not edit by hand.\n",
        f"- **Total Tickets Resolved:** {len(runs)}" + (f" ({estimated} estimated)" if estimated else ""),
        f"- **Total Tokens Consumed:** {sum(tokens):,}",
        f"- **Grand Total Expenditure:** **${total_cost:.4f} USD**\n",
        "| Date | Ticket | Summary | Tool | Model | QA Rounds | Tokens | Cost (USD) | Source | Commit |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r, tok in zip(runs, tokens):
        rounds = r.get("qa", {}).get("rounds")
        lines.append(
            f"| {r.get('finished_at', '')} | **{r.get('ticket', '')}** | {r.get('summary', '')} | {r.get('tool', '')} | "
            f"{r.get('model', '')} | {rounds if rounds is not None else '-'} | {tok:,} | ${r.get('cost_usd', 0.0):.4f} | "
            f"{'estimated' if r.get('estimated') else 'measured'} | `{r.get('commit', '')}` |"
        )
    label = f"{len(runs)} ticket{'s' if len(runs) != 1 else ''} completed"
    lines.append(f"| **TOTAL** | | **{label}** | | | | **{sum(tokens):,}** | **${total_cost:.4f} USD** | | |\n")

    md_path = get_costs_md_path()
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def log_ticket_completion(ticket_key, summary=None, branch=None, since=None, model_override=None, post_jira=True,
                          base_branch=None, qa_rounds=None, ac=None, tool=None):
    """Write the run record for a delivered ticket to dev/runs.json and regenerate dev/COSTS.md."""
    session = load_session()
    report = generate_cost_report(since, model_override, base_branch)
    branch = branch or git_value("rev-parse", "--abbrev-ref", "HEAD")

    run = {
        "ticket": ticket_key,
        "summary": summary or f"Task {ticket_key}",
        "branch": branch,
        "base_branch": base_branch or "main",
        "commit": git_value("rev-parse", "--short", "HEAD"),
        "kit_version": kit_version(),
        "tool": detect_tool(tool, report),
        "model": model_label(report),
        "started_at": report.get("since") or since or session.get("since"),
        "finished_at": utc_now(),
        "qa": {"verdict": "APPROVED", "rounds": qa_rounds, "acceptance_criteria": parse_ac(ac)},
        "estimated": bool(report.get("estimated")),
        "cost_usd": report["cost_usd"],
        "usage": {k: report.get(k) for k in ("source", "since", "models", "pricing_as_of", "totals", "agents")},
        "delivery": {"pushed": False, "jira_status": None},
    }

    data = load_runs()
    data["runs"] = [r for r in data["runs"]
                    if not (r.get("ticket") == ticket_key and r.get("branch") == branch)] + [run]
    save_runs(data)

    if post_jira:
        try:
            from jira_sync import comment_ticket
            comment_ticket(ticket_key, (
                f"✅ Squad development complete · Quality Gate: APPROVED\n"
                f"• Branch: {run['branch']} · Commit: {run['commit']}\n"
                f"• Tokens: {run['usage']['totals']['total_tokens']:,}\n"
                f"• Development Cost: ${run['cost_usd']:.4f} USD{estimated_tag(report)} ({run['model']})"
            ))
        except Exception as e:
            print(f"Note: Could not post comment to Jira: {e}", file=sys.stderr)

    reset_session(quiet=True)
    return run


def record_delivery(ticket_key, pushed=None, jira_status=None):
    """Update the latest run of a ticket after Checkpoint 2 (push, Jira transition)."""
    data = load_runs()
    for run in reversed(data["runs"]):
        if run.get("ticket") == ticket_key:
            delivery = run.setdefault("delivery", {"pushed": False, "jira_status": None})
            if pushed is not None:
                delivery["pushed"] = pushed
            if jira_status is not None:
                delivery["jira_status"] = jira_status
            save_runs(data)
            return run
    return None


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

    log_p = subparsers.add_parser("log", help="Write the run record to dev/runs.json and regenerate dev/COSTS.md")
    log_p.add_argument("--ticket", required=True, help="Jira ticket key (e.g. PAS-1)")
    log_p.add_argument("--summary", default=None, help="Ticket summary/title")
    log_p.add_argument("--branch", default=None, help="Feature branch (default: current branch)")
    log_p.add_argument("--base-branch", default=None, help="Base branch (default: main)")
    log_p.add_argument("--qa-rounds", type=int, default=None, help="QA verifier rounds until APPROVED")
    log_p.add_argument("--ac", default=None, help="Acceptance Criteria verified, as VERIFIED/TOTAL (e.g. 3/3)")
    log_p.add_argument("--tool", default=None, help="Tool override (default: detected)")
    log_p.add_argument("--since", default=None, help="Start time, ISO 8601 UTC (default: dev/session.json)")
    log_p.add_argument("--model", default=None, help="Model override")
    log_p.add_argument("--no-jira", action="store_true", help="Do not post Jira comment")

    del_p = subparsers.add_parser("deliver", help="Record the outcome of Checkpoint 2 on the latest run of a ticket")
    del_p.add_argument("--ticket", required=True, help="Jira ticket key (e.g. PAS-1)")
    del_p.add_argument("--pushed", action="store_true", help="The feature branch was pushed")
    del_p.add_argument("--jira-status", default=None, help="Status the ticket was moved to")

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
        run = log_ticket_completion(args.ticket, args.summary, args.branch, args.since, args.model, not args.no_jira,
                                    args.base_branch, args.qa_rounds, args.ac, args.tool)
        tag = " · estimated" if run["estimated"] else ""
        print(f"✅ Logged {run['ticket']} (${run['cost_usd']:.4f} USD · "
              f"{run['usage']['totals']['total_tokens']:,} tokens{tag}) to dev/runs.json and dev/COSTS.md")
    elif args.command == "deliver":
        run = record_delivery(args.ticket, args.pushed or None, args.jira_status)
        if not run:
            print(f"No run recorded for {args.ticket} in dev/runs.json", file=sys.stderr)
            return 1
        print(f"✅ {args.ticket}: pushed={run['delivery']['pushed']} · jira={run['delivery']['jira_status']}")
    elif args.command == "reset":
        reset_session()
    return 0


if __name__ == "__main__":
    sys.exit(main())
