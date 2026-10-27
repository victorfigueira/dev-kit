#!/usr/bin/env python3
"""Sum the tokens a ticket consumed, from Claude Code or Antigravity local session files.

Ported from audit-kit's usage_report.py. Usage (from the project root):
  python3 dev-kit/tools/usage_report.py --since 2026-10-27T10:00:00Z [--engine auto|claude|antigravity]

Supports:
- Claude Code: reads ~/.claude/projects/<encoded project path>/ (main sessions and subagent logs)
- Antigravity: reads ~/.gemini/antigravity/brain/<conversation-id>/.system_generated/logs/transcript.jsonl
  and the transcripts of subagents started with invoke_subagent.

Counts only records at or after --since. Tokens are attributed to a squad role from the
`dev-kit-agent: <name>` header that starts every subagent prompt (see RUN.md "Subagents");
the main session is the orchestrator. Reads numbers, model names and agent tags only,
never copies user code. Prints JSON; "available": false when no session files are found.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re

TYPES = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
TAG = re.compile(r"dev-kit-agent:\s*([a-z0-9-]+)", re.I)

ROLES = {
    "orchestrator": "Orchestrator (main session)",
    "pm": "Project Manager & Tech Lead",
    "database": "Database Engineer (DBA)",
    "backend": "Backend Developer",
    "frontend": "Frontend Developer",
    "qa": "QA Engineer (Quality Gate)",
}

# Subagent file names and Antigravity roles that map to a squad role.
ALIASES = {
    "database-engineer": "database",
    "dba": "database",
    "backend-dev": "backend",
    "frontend-dev": "frontend",
    "qa-verifier": "qa",
    "quality-gate": "qa",
}

# Fallback only, for subagents started without the tag. Order matters.
AGENT_HINTS = [
    ("qa", r"qa[\s_-]*verifier|quality gate|agents/qa\.md"),
    ("pm", r"agents/pm\.md|technical plan|tech lead"),
    ("database", r"database[\s_-]*engineer|agents/database\.md|migration"),
    ("backend", r"backend[\s_-]*dev|agents/backend\.md"),
    ("frontend", r"frontend[\s_-]*dev|agents/frontend\.md"),
]

PRICING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pricing.json")


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

def load_pricing(root="."):
    """Load tools/pricing.json, with dev/pricing.json models tried first when present."""
    with open(PRICING_FILE, encoding="utf-8") as fh:
        table = json.load(fh)
    override = os.path.join(root, "dev", "pricing.json")
    if os.path.isfile(override):
        try:
            with open(override, encoding="utf-8") as fh:
                extra = json.load(fh)
            table["models"] = extra.get("models", []) + table["models"]
            table["default"] = extra.get("default", table["default"])
        except (OSError, ValueError):
            pass
    return table


def normalize_model(name):
    return re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")


def match_pricing(model_name, table):
    """Return the pricing entry for a model name, or the table's default."""
    norm = normalize_model(model_name)
    if norm:
        for entry in table["models"]:
            if re.search(entry["pattern"], norm):
                return entry
    return table["default"]


def cost_of(counts, model_name, table, cache_write_1h=0):
    """USD cost of one model's token counts. cache_write_1h is the part of cache writes on the 1h TTL."""
    p = match_pricing(model_name, table)
    cw_1h = min(cache_write_1h, counts.get("cache_creation_input_tokens", 0))
    cw_5m = counts.get("cache_creation_input_tokens", 0) - cw_1h
    total = (
        counts.get("input_tokens", 0) * p["input"]
        + counts.get("output_tokens", 0) * p["output"]
        + cw_5m * p["cache_write"]
        + cw_1h * p.get("cache_write_1h", p["cache_write"])
        + counts.get("cache_read_input_tokens", 0) * p["cache_read"]
    ) / 1_000_000.0
    return total


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def parse_ts(value):
    try:
        ts = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=dt.timezone.utc)


def read_jsonl(path):
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def role_from_name(name):
    name = (name or "").lower()
    name = ALIASES.get(name, name)
    return name if name in ROLES else None


def agent_name_from_text(text, fallback):
    if text:
        tag = TAG.search(text[:500])
        if tag:
            return role_from_name(tag.group(1)) or tag.group(1).lower()
        head = text[:300].lower()
        for name, pattern in AGENT_HINTS:
            if re.search(pattern, head):
                return name
    return fallback


class Tally:
    """Token counts per agent and per model, so each model is priced at its own rate."""

    def __init__(self):
        self.agents = {}

    def add(self, agent, model, counts, cache_write_1h=0, run=False):
        a = self.agents.setdefault(agent, {"runs": 0, "models": {}})
        if run:
            a["runs"] += 1
        m = a["models"].setdefault(model or "unknown", {**{t: 0 for t in TYPES}, "cache_write_1h": 0})
        for t in TYPES:
            m[t] += counts.get(t, 0)
        m["cache_write_1h"] += cache_write_1h

    def result(self, table, source, since_str, notes):
        agents = []
        model_use = {}
        for name, a in self.agents.items():
            counts = {t: sum(m[t] for m in a["models"].values()) for t in TYPES}
            if sum(counts.values()) == 0:
                continue
            cost = 0.0
            for model, m in a["models"].items():
                cost += cost_of(m, model, table, m["cache_write_1h"])
                model_use[model] = model_use.get(model, 0) + sum(m[t] for t in TYPES)
            agents.append({
                "agent": name,
                "name": ROLES.get(name, name),
                "runs": max(1, a["runs"]),
                **counts,
                "total_tokens": sum(counts.values()),
                "cost_usd": round(cost, 4),
            })
        if not agents:
            return None
        order = list(ROLES)
        agents.sort(key=lambda x: order.index(x["agent"]) if x["agent"] in order else len(order))
        totals = {t: sum(a[t] for a in agents) for t in TYPES}
        totals["total_tokens"] = sum(totals[t] for t in TYPES)
        models = sorted(model_use, key=lambda k: -model_use[k])
        return {
            "available": True,
            "estimated": False,
            "source": source,
            "since": since_str,
            "models": models,
            "pricing": {m: match_pricing(m, table)["label"] for m in models},
            "pricing_as_of": table.get("as_of"),
            "totals": totals,
            "cost_usd": round(sum(a["cost_usd"] for a in agents), 4),
            "agents": agents,
            "notes": notes,
        }


# ---------------------------------------------------------------------------
# Claude Code session parsing
# ---------------------------------------------------------------------------

def claude_project_dir(root):
    base = os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude"))
    encoded = re.sub(r"[^A-Za-z0-9-]", "-", os.path.abspath(root))
    path = os.path.join(base, "projects", encoded)
    return path if os.path.isdir(path) else None


def first_user_text_claude(records):
    for r in records:
        if r.get("type") == "user":
            c = r.get("message", {}).get("content")
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                return " ".join(b.get("text", "") for b in c if isinstance(b, dict))
    return ""


def tally_claude_records(records, since, seen, tally, agent):
    found = False
    for r in records:
        msg = r.get("message") or {}
        usage = msg.get("usage")
        if r.get("type") != "assistant" or not usage:
            continue
        ts = parse_ts(r.get("timestamp"))
        if since and (ts is None or ts < since):
            continue
        key = msg.get("id") or r.get("requestId") or r.get("uuid")
        if key in seen:
            continue
        seen.add(key)
        counts = {t: int(usage.get(t) or 0) for t in TYPES}
        cw_1h = int((usage.get("cache_creation") or {}).get("ephemeral_1h_input_tokens") or 0)
        tally.add(agent, msg.get("model"), counts, cw_1h, run=not found)
        found = True
    return found


def process_claude(pdir, since, since_str, table):
    sessions = sorted(glob.glob(os.path.join(pdir, "*.jsonl")), key=os.path.getmtime)
    if since:
        sessions = [s for s in sessions
                    if dt.datetime.fromtimestamp(os.path.getmtime(s), dt.timezone.utc) >= since]
    else:
        sessions = sessions[-1:]
    if not sessions:
        return None

    tally = Tally()
    seen = set()
    for main_file in sessions:
        sid = os.path.splitext(os.path.basename(main_file))[0]
        records = read_jsonl(main_file)
        tally_claude_records([r for r in records if not r.get("isSidechain")], since, seen, tally, "orchestrator")
        groups = [read_jsonl(f) for f in sorted(set(
            glob.glob(os.path.join(pdir, sid, "subagents", "*.jsonl"))
            + glob.glob(os.path.join(pdir, sid, "agent-*.jsonl"))))]
        sidechain = [r for r in records if r.get("isSidechain")]
        if sidechain:
            groups.append(sidechain)
        for i, recs in enumerate(groups, 1):
            agent = agent_name_from_text(first_user_text_claude(recs), f"subagent-{i}")
            tally_claude_records(recs, since, seen, tally, agent)

    return tally.result(table, "Claude Code session files", since_str,
                        "Counted from local Claude Code logs. Roles matched from the dev-kit-agent header of each subagent prompt.")


# ---------------------------------------------------------------------------
# Antigravity session parsing
# ---------------------------------------------------------------------------

MODEL_SELECTION = re.compile(r"Model Selection`?\s+from\s+.*?\s+to\s+([A-Za-z0-9. ()-]+?)(?:\.\s+[A-Z]|\.\s*</|\.?\s*$|\n)")


def antigravity_brain_dir():
    for c in (os.environ.get("ANTIGRAVITY_APP_DATA_DIR"), os.environ.get("GEMINI_DATA_DIR"),
              os.path.expanduser("~/.gemini/antigravity"),
              os.path.expanduser("~/Library/Application Support/Antigravity")):
        if c and os.path.isdir(os.path.join(c, "brain")):
            return os.path.join(c, "brain")
    return None


def transcript_path(brain_dir, conv_id):
    return os.path.join(brain_dir, conv_id, ".system_generated", "logs", "transcript.jsonl")


def find_antigravity_transcript(root, since=None, conv_id=None):
    brain_dir = antigravity_brain_dir()
    if not brain_dir:
        return None, None
    target = conv_id or os.environ.get("ANTIGRAVITY_CONVERSATION_ID")
    if target and os.path.isfile(transcript_path(brain_dir, target)):
        return transcript_path(brain_dir, target), brain_dir

    root_abs = os.path.abspath(root)
    files = sorted(glob.glob(transcript_path(brain_dir, "*")), key=os.path.getmtime, reverse=True)
    for path in files:
        if since and dt.datetime.fromtimestamp(os.path.getmtime(path), dt.timezone.utc) < since:
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                head = "".join(fh.readline() for _ in range(8))
        except OSError:
            continue
        if root_abs in head:
            return path, brain_dir
    return None, brain_dir


def extract_subagent_cids(records):
    """Subagents started with invoke_subagent: list of (role, conversation_id)."""
    subagents = []
    pending = None
    for r in records:
        for tc in r.get("tool_calls") or []:
            if tc.get("name") == "invoke_subagent":
                args = tc.get("args") or {}
                role = re.sub(r"[^a-z0-9]+", "-", str(args.get("Role") or "subagent").lower()).strip("-")
                pending = agent_name_from_text(str(args.get("Prompt") or ""), role_from_name(role) or role)
        content = r.get("content") or ""
        if pending and isinstance(content, str):
            m = (re.search(r'["\']?conversationId["\']?\s*:\s*["\']([a-f0-9-]{36})["\']', content, re.I)
                 or re.search(r"([a-f0-9]{8}-[a-f0-9-]{27})", content))
            if m:
                subagents.append((pending, m.group(1)))
                pending = None
    return subagents


def tally_antigravity_file(path, since, tally, agent):
    records = read_jsonl(path)
    model = None
    found = False
    for r in records:
        c = r.get("content")
        if isinstance(c, str) and "Model Selection" in c:
            m = MODEL_SELECTION.search(c)
            if m and m.group(1).strip():
                model = m.group(1).strip()
        ts = parse_ts(r.get("created_at"))
        if since and ts and ts < since:
            continue
        if "input_tokens" in r or "output_tokens" in r:
            counts = {
                "input_tokens": int(r.get("input_tokens") or 0),
                "output_tokens": int(r.get("output_tokens") or 0),
                "cache_read_input_tokens": int(r.get("cache_read_tokens") or 0),
                "cache_creation_input_tokens": int(r.get("cache_creation_input_tokens") or 0),
            }
            tally.add(agent, model or "Gemini (Antigravity)", counts, run=not found)
            found = True
    return records


def process_antigravity(path, brain_dir, since, since_str, table):
    tally = Tally()
    records = tally_antigravity_file(path, since, tally, "orchestrator")
    for agent, cid in extract_subagent_cids(records):
        sub = transcript_path(brain_dir, cid)
        if os.path.isfile(sub):
            tally_antigravity_file(sub, since, tally, agent)
    return tally.result(table, "Antigravity session transcripts", since_str,
                        "Counted from local Antigravity transcripts. Subagent tokens attributed through invoke_subagent conversations.")


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def detect_model(root=".", since=None):
    """Most-used model in the recent session files, or None."""
    res = collect(root, since)
    return res["models"][0] if res.get("available") and res.get("models") else None


def collect(root=".", since_str=None, engine="auto", conversation_id=None):
    """Measure usage from session files. Returns a report dict, or {"available": False, ...}."""
    since = parse_ts(since_str) if since_str else None
    table = load_pricing(root)

    def antigravity():
        path, brain = find_antigravity_transcript(root, since, conversation_id)
        return process_antigravity(path, brain, since, since_str, table) if path else None

    def claude():
        pdir = claude_project_dir(root)
        return process_claude(pdir, since, since_str, table) if pdir else None

    if engine == "antigravity":
        order = [antigravity]
    elif engine == "claude":
        order = [claude]
    elif os.environ.get("ANTIGRAVITY_AGENT") or os.environ.get("ANTIGRAVITY_CONVERSATION_ID"):
        order = [antigravity, claude]
    else:
        order = [claude, antigravity]

    for fn in order:
        res = fn()
        if res:
            return res
    return {"available": False, "reason": "No Claude Code or Antigravity session files found for this project and time range."}


def main():
    ap = argparse.ArgumentParser(description="Sum ticket tokens from local AI session files.")
    ap.add_argument("--since", help="ticket start time, ISO 8601 (UTC)")
    ap.add_argument("--root", default=".", help="project root directory (default: .)")
    ap.add_argument("--engine", choices=["auto", "claude", "antigravity"], default="auto")
    ap.add_argument("--conversation-id", help="Antigravity conversation ID if known")
    args = ap.parse_args()
    print(json.dumps(collect(args.root, args.since, args.engine, args.conversation_id), indent=2))


if __name__ == "__main__":
    main()
