#!/usr/bin/env python3
"""Token and USD Cost Calculation Engine for dev-kit.

Tracks and estimates token consumption and development cost in USD across all squad roles.
Maintains a cumulative cost ledger across tickets in dev/COSTS.md and dev/cost_ledger.json.

Usage:
  python3 dev-kit/tools/cost_tracker.py report [--model MODEL] [--json]
  python3 dev-kit/tools/cost_tracker.py log --ticket TICKET_KEY [--summary TITLE] [--branch BRANCH] [--model MODEL]
  python3 dev-kit/tools/cost_tracker.py record --layer LAYER --input-tokens N --output-tokens M [--model MODEL]
  python3 dev-kit/tools/cost_tracker.py estimate [--base-branch BRANCH] [--model MODEL] [--json]
  python3 dev-kit/tools/cost_tracker.py reset
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

# Pricing per 1,000,000 tokens (USD)
MODEL_PRICING = {
    "claude-3-7-sonnet": {"input": 3.00, "output": 15.00, "name": "Claude 3.7 Sonnet"},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00, "name": "Claude 3.5 Sonnet"},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00, "name": "Claude 3.5 Haiku"},
    "claude-3-opus": {"input": 15.00, "output": 75.00, "name": "Claude 3 Opus"},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00, "name": "Gemini 2.5 Pro"},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40, "name": "Gemini 2.0 Flash"},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00, "name": "Gemini 1.5 Pro"},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30, "name": "Gemini 1.5 Flash"},
    "gpt-4o": {"input": 2.50, "output": 10.00, "name": "GPT-4o"},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "name": "GPT-4o mini"},
    "o3-mini": {"input": 1.10, "output": 4.40, "name": "o3-mini"}
}

DEFAULT_MODEL = "claude-3-7-sonnet"


def get_cost_file_path():
    """Locate session cost file in dev/ directory."""
    cwd = os.getcwd()
    return os.path.join(cwd, "dev", "session_cost.json")


def get_ledger_file_path():
    """Locate cumulative cost ledger file in dev/ directory."""
    cwd = os.getcwd()
    return os.path.join(cwd, "dev", "cost_ledger.json")


def get_costs_md_path():
    """Locate cumulative COSTS.md ledger in dev/ directory."""
    cwd = os.getcwd()
    return os.path.join(cwd, "dev", "COSTS.md")


def detect_active_model(model_override=None):
    """Detect current model from override, environment, or default."""
    if model_override:
        clean = model_override.lower().strip()
        for k in MODEL_PRICING:
            if k in clean or clean in k:
                return k

    env_model = os.environ.get("DEV_KIT_MODEL") or os.environ.get("CLAUDE_MODEL") or os.environ.get("AI_MODEL")
    if env_model:
        clean = env_model.lower().strip()
        for k in MODEL_PRICING:
            if k in clean or clean in k:
                return k

    return DEFAULT_MODEL


def calculate_cost(input_tokens, output_tokens, model_key=DEFAULT_MODEL):
    """Calculate exact USD cost for given token counts."""
    pricing = MODEL_PRICING.get(model_key, MODEL_PRICING[DEFAULT_MODEL])
    in_cost = (input_tokens / 1_000_000.0) * pricing["input"]
    out_cost = (output_tokens / 1_000_000.0) * pricing["output"]
    return round(in_cost + out_cost, 4)


def load_session_data():
    """Load session cost data or return empty structure."""
    path = get_cost_file_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"layers": {}, "model": DEFAULT_MODEL}


def save_session_data(data):
    """Save session cost data into dev/session_cost.json."""
    path = get_cost_file_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def record_layer_usage(layer, input_tokens, output_tokens, model_override=None):
    """Record token consumption for a specific squad layer."""
    model_key = detect_active_model(model_override)
    data = load_session_data()
    data["model"] = model_key
    if "layers" not in data:
        data["layers"] = {}

    data["layers"][layer] = {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "cost_usd": calculate_cost(int(input_tokens), int(output_tokens), model_key)
    }
    save_session_data(data)
    return data["layers"][layer]


def estimate_from_diff(base_branch=None, model_override=None):
    """Estimate token usage and USD cost from git diff and workspace artifacts."""
    model_key = detect_active_model(model_override)
    target_branch = base_branch or "main"

    # 1. Measure diff size
    diff_chars = 0
    try:
        res = subprocess.run(["git", "diff", target_branch], capture_output=True, text=True)
        if res.returncode == 0:
            diff_chars = len(res.stdout)
    except Exception:
        diff_chars = 4000

    # 2. Measure PLAN.md size if present
    plan_chars = 0
    plan_path = os.path.join(os.getcwd(), "dev", "PLAN.md")
    if os.path.exists(plan_path):
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                plan_chars = len(f.read())
        except Exception:
            pass

    # Approximate 4 characters per token
    base_diff_tokens = max(500, diff_chars // 4)
    base_plan_tokens = max(400, plan_chars // 4)

    layers_distribution = {
        "pm": {"name": "Project Manager & Tech Lead", "in_ratio": 2.5, "out_ratio": 0.8},
        "database": {"name": "Database Engineer (DBA)", "in_ratio": 1.5, "out_ratio": 0.5},
        "backend": {"name": "Backend Developer", "in_ratio": 3.0, "out_ratio": 1.2},
        "frontend": {"name": "Frontend Developer", "in_ratio": 2.8, "out_ratio": 1.0},
        "qa": {"name": "QA Engineer (Quality Gate)", "in_ratio": 2.0, "out_ratio": 0.4}
    }

    layers_result = {}
    total_in = 0
    total_out = 0

    base_turn_tokens = base_diff_tokens + base_plan_tokens
    for key, info in layers_distribution.items():
        in_tokens = int(base_turn_tokens * info["in_ratio"]) + 2500
        out_tokens = int(base_turn_tokens * info["out_ratio"]) + 600
        cost = calculate_cost(in_tokens, out_tokens, model_key)
        layers_result[key] = {
            "name": info["name"],
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "cost_usd": cost
        }
        total_in += in_tokens
        total_out += out_tokens

    total_cost = calculate_cost(total_in, total_out, model_key)
    pricing = MODEL_PRICING.get(model_key, MODEL_PRICING[DEFAULT_MODEL])

    return {
        "model_key": model_key,
        "model_name": pricing["name"],
        "pricing": pricing,
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "total_tokens": total_in + total_out,
        "total_cost_usd": total_cost,
        "layers": layers_result,
        "estimated": True
    }


def generate_cost_report(model_override=None):
    """Generate final cost summary from recorded session data or fallback to estimate."""
    data = load_session_data()
    model_key = detect_active_model(model_override or data.get("model"))
    pricing = MODEL_PRICING.get(model_key, MODEL_PRICING[DEFAULT_MODEL])

    if not data.get("layers"):
        return estimate_from_diff(model_override=model_key)

    layers_result = {}
    total_in = 0
    total_out = 0

    role_names = {
        "pm": "Project Manager & Tech Lead",
        "database": "Database Engineer (DBA)",
        "backend": "Backend Developer",
        "frontend": "Frontend Developer",
        "qa": "QA Engineer (Quality Gate)"
    }

    for key, metrics in data["layers"].items():
        in_tok = metrics.get("input_tokens", 0)
        out_tok = metrics.get("output_tokens", 0)
        cost = calculate_cost(in_tok, out_tok, model_key)
        layers_result[key] = {
            "name": role_names.get(key, key),
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cost_usd": cost
        }
        total_in += in_tok
        total_out += out_tok

    total_cost = calculate_cost(total_in, total_out, model_key)
    return {
        "model_key": model_key,
        "model_name": pricing["name"],
        "pricing": pricing,
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "total_tokens": total_in + total_out,
        "total_cost_usd": total_cost,
        "layers": layers_result,
        "estimated": False
    }


def format_markdown(report):
    """Format the cost report into GitHub-flavored markdown."""
    md = []
    md.append("### Development Cost & Token Consumption\n")
    md.append(f"- **AI Model:** {report['model_name']} (`${report['pricing']['input']:.2f}`/1M in · `${report['pricing']['output']:.2f}`/1M out)")
    md.append(f"- **Total Tokens:** {report['total_tokens']:,} ({report['total_input_tokens']:,} input · {report['total_output_tokens']:,} output)")
    md.append(f"- **Total Development Cost:** **${report['total_cost_usd']:.4f} USD**\n")

    md.append("| Squad Role / Phase | Input Tokens | Output Tokens | Total Tokens | Cost (USD) |")
    md.append("|---|---|---|---|---|")
    for _, l in report["layers"].items():
        t_tokens = l["input_tokens"] + l["output_tokens"]
        md.append(f"| **{l['name']}** | {l['input_tokens']:,} | {l['output_tokens']:,} | {t_tokens:,} | ${l['cost_usd']:.4f} |")
    md.append(f"| **Total Squad Execution** | **{report['total_input_tokens']:,}** | **{report['total_output_tokens']:,}** | **{report['total_tokens']:,}** | **${report['total_cost_usd']:.4f} USD** |\n")

    return "\n".join(md)


def render_costs_markdown(ledger):
    """Render cumulative COSTS.md summary table."""
    md_path = get_costs_md_path()
    total_tokens = sum(e.get("total_tokens", 0) for e in ledger)
    total_cost = sum(e.get("cost_usd", 0.0) for e in ledger)

    lines = [
        "# Project Development Cost & Token Ledger\n",
        "Cumulative token consumption and expenditure tracked across all resolved tickets in `dev-kit`.\n",
        f"- **Total Tickets Resolved:** {len(ledger)}",
        f"- **Total Tokens Consumed:** {total_tokens:,}",
        f"- **Grand Total Expenditure:** **${total_cost:.4f} USD**\n",
        "| Date | Ticket | Summary | Model | Tokens | Cost (USD) | Branch |",
        "|---|---|---|---|---|---|---|"
    ]

    for e in ledger:
        lines.append(
            f"| {e['date']} | **{e['ticket']}** | {e.get('summary', '')} | {e.get('model', '')} | {e.get('total_tokens', 0):,} | ${e.get('cost_usd', 0.0):.4f} | `{e.get('branch', '')}` |"
        )

    ticket_label = f"{len(ledger)} ticket{'s' if len(ledger) != 1 else ''} completed"
    lines.append(f"| **TOTAL** | | **{ticket_label}** | | **{total_tokens:,}** | **${total_cost:.4f} USD** | |\n")

    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def log_ticket_completion(ticket_key, summary=None, branch=None, model_override=None, post_jira=True):
    """Log completed ticket to persistent ledger (dev/cost_ledger.json, dev/COSTS.md, and Jira)."""
    report = generate_cost_report(model_override)
    ledger_path = get_ledger_file_path()

    ledger = []
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
        except Exception:
            ledger = []

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    clean_branch = branch or f"feat/{ticket_key}"

    entry = {
        "date": now_str,
        "ticket": ticket_key,
        "summary": summary or f"Task {ticket_key}",
        "branch": clean_branch,
        "model": report["model_name"],
        "input_tokens": report["total_input_tokens"],
        "output_tokens": report["total_output_tokens"],
        "total_tokens": report["total_tokens"],
        "cost_usd": report["total_cost_usd"]
    }

    # Replace existing entry for ticket if already logged, otherwise append
    replaced = False
    for i, item in enumerate(ledger):
        if item.get("ticket") == ticket_key:
            ledger[i] = entry
            replaced = True
            break
    if not replaced:
        ledger.append(entry)

    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)

    render_costs_markdown(ledger)

    # Post comment to Jira ticket
    if post_jira:
        try:
            try:
                from tools.jira_sync import comment_ticket
            except ImportError:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from jira_sync import comment_ticket
            comment_msg = (
                f"✅ Squad development complete · Quality Gate: APPROVED\n"
                f"• Branch: {entry['branch']}\n"
                f"• Tokens: {entry['total_tokens']:,} ({entry['input_tokens']:,} in · {entry['output_tokens']:,} out)\n"
                f"• Development Cost: ${entry['cost_usd']:.4f} USD ({entry['model']})\n"
                f"• PR Document: dev/PR_{ticket_key}.md"
            )
            comment_ticket(ticket_key, comment_msg)
        except Exception as e:
            print(f"Note: Could not post comment to Jira: {e}", file=sys.stderr)

    # Reset current session cost for next ticket
    reset_session()
    return entry


def reset_session():
    """Reset the current session cost tracker file."""
    path = get_cost_file_path()
    if os.path.exists(path):
        os.remove(path)
    print("✅ Session cost data reset.")


def main():
    parser = argparse.ArgumentParser(description="dev-kit Token and USD Cost Calculation Engine.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Report
    rep_p = subparsers.add_parser("report", help="Generate cost and token consumption report")
    rep_p.add_argument("--model", default=None, help="Model override")
    rep_p.add_argument("--json", action="store_true", help="Output JSON format")

    # Log
    log_p = subparsers.add_parser("log", help="Log ticket completion to cumulative ledger and Jira")
    log_p.add_argument("--ticket", required=True, help="Jira ticket key (e.g. PAS-1)")
    log_p.add_argument("--summary", default=None, help="Ticket summary/title")
    log_p.add_argument("--branch", default=None, help="Git branch name")
    log_p.add_argument("--model", default=None, help="Model override")
    log_p.add_argument("--no-jira", action="store_true", help="Do not post Jira comment")

    # Record
    rec_p = subparsers.add_parser("record", help="Record layer token usage")
    rec_p.add_argument("--layer", required=True, choices=["pm", "database", "backend", "frontend", "qa"], help="Squad layer")
    rec_p.add_argument("--input-tokens", required=True, type=int, help="Input tokens")
    rec_p.add_argument("--output-tokens", required=True, type=int, help="Output tokens")
    rec_p.add_argument("--model", default=None, help="Model name")

    # Estimate
    est_p = subparsers.add_parser("estimate", help="Estimate cost from git diff and artifacts")
    est_p.add_argument("--base-branch", default="main", help="Base branch for diff comparison")
    est_p.add_argument("--model", default=None, help="Model override")
    est_p.add_argument("--json", action="store_true", help="Output JSON format")

    # Reset
    subparsers.add_parser("reset", help="Reset session cost data")

    args = parser.parse_args()

    if args.command == "record":
        res = record_layer_usage(args.layer, args.input_tokens, args.output_tokens, args.model)
        print(f"✅ Recorded {args.layer}: {args.input_tokens:,} in / {args.output_tokens:,} out (${res['cost_usd']:.4f} USD)")
        return 0

    elif args.command == "report":
        report = generate_cost_report(args.model)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(format_markdown(report))
        return 0

    elif args.command == "log":
        entry = log_ticket_completion(
            ticket_key=args.ticket,
            summary=args.summary,
            branch=args.branch,
            model_override=args.model,
            post_jira=not args.no_jira
        )
        print(f"✅ Logged {entry['ticket']} (${entry['cost_usd']:.4f} USD · {entry['total_tokens']:,} tokens) to dev/COSTS.md and dev/cost_ledger.json")
        return 0

    elif args.command == "estimate":
        report = estimate_from_diff(args.base_branch, args.model)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(format_markdown(report))
        return 0

    elif args.command == "reset":
        reset_session()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
