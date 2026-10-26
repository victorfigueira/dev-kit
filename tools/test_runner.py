#!/usr/bin/env python3
"""Universal Test Suite Runner for dev-kit.

Auto-detects project tech stack (Node.js, Python, Go, Rust, .NET) or reads
custom commands from project-context.md, runs test suites, and returns
structured execution results for the QA Verifier.

Usage:
  python3 dev-kit/tools/test_runner.py [--project-dir DIR] [--typecheck] [--lint] [--json]
"""
import argparse
import json
import os
import re
import subprocess
import sys


def parse_context_file(context_path):
    """Extract custom test commands from project-context.md if present."""
    if not os.path.exists(context_path):
        return {}
    commands = {}
    try:
        with open(context_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Look for commands in backticks (supporting markdown bold)
        test_match = re.search(r"Unit & Integration Tests:?\*{0,2}\s*`([^`]+)`", content, re.IGNORECASE)
        if test_match:
            commands["test"] = test_match.group(1).strip()
        typecheck_match = re.search(r"Type Checking:?\*{0,2}\s*`([^`]+)`", content, re.IGNORECASE)
        if typecheck_match:
            commands["typecheck"] = typecheck_match.group(1).strip()
        lint_match = re.search(r"Linting & Code Style:?\*{0,2}\s*`([^`]+)`", content, re.IGNORECASE)
        if lint_match:
            commands["lint"] = lint_match.group(1).strip()
    except Exception:
        pass
    return commands


def detect_test_commands(project_dir="."):
    """Auto-detect test, typecheck, and lint commands based on project files."""
    # Check project-context.md first
    for candidate in [
        os.path.join(project_dir, "dev", "project-context.md"),
        os.path.join(project_dir, "project-context.md"),
        os.path.join(project_dir, "dev-kit", "templates", "project-context.md")
    ]:
        custom = parse_context_file(candidate)
        if custom and "test" in custom:
            return custom

    # 1. Node.js (package.json)
    pkg_json = os.path.join(project_dir, "package.json")
    if os.path.exists(pkg_json):
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            scripts = data.get("scripts", {})
            test_cmd = "npm test"
            if os.path.exists(os.path.join(project_dir, "pnpm-lock.yaml")):
                test_cmd = "pnpm test"
            elif os.path.exists(os.path.join(project_dir, "yarn.lock")):
                test_cmd = "yarn test"
            elif os.path.exists(os.path.join(project_dir, "bun.lockb")):
                test_cmd = "bun test"

            cmds = {"test": test_cmd}
            if "typecheck" in scripts or "type-check" in scripts:
                cmds["typecheck"] = test_cmd.split()[0] + " run typecheck"
            if "lint" in scripts:
                cmds["lint"] = test_cmd.split()[0] + " run lint"
            return cmds
        except Exception:
            return {"test": "npm test"}

    # 2. Python (pytest / pyproject.toml / requirements.txt)
    if (
        os.path.exists(os.path.join(project_dir, "pytest.ini"))
        or os.path.exists(os.path.join(project_dir, "pyproject.toml"))
        or os.path.exists(os.path.join(project_dir, "requirements.txt"))
        or os.path.exists(os.path.join(project_dir, "tests"))
    ):
        cmds = {"test": "pytest"}
        if os.path.exists(os.path.join(project_dir, "mypy.ini")) or "mypy" in os.listdir(project_dir):
            cmds["typecheck"] = "mypy ."
        return cmds

    # 3. Go (go.mod)
    if os.path.exists(os.path.join(project_dir, "go.mod")):
        return {"test": "go test ./..."}

    # 4. Rust (Cargo.toml)
    if os.path.exists(os.path.join(project_dir, "Cargo.toml")):
        return {"test": "cargo test", "typecheck": "cargo check", "lint": "cargo clippy"}

    # 5. .NET (*.csproj, *.sln)
    for f in os.listdir(project_dir):
        if f.endswith(".csproj") or f.endswith(".sln"):
            return {"test": "dotnet test"}

    return {"test": None}


def run_command(command, cwd="."):
    """Run shell command safely and capture output."""
    if not command:
        return {
            "status": "not_configured",
            "command": None,
            "exit_code": 0,
            "stdout": "",
            "stderr": "No test command detected or configured."
        }
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300
        )
        return {
            "status": "passed" if proc.returncode == 0 else "failed",
            "command": command,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": "Command timed out after 300 seconds."
        }
    except Exception as e:
        return {
            "status": "error",
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description="Universal test runner for dev-kit QA Verifier.")
    parser.add_argument("--project-dir", default=".", help="Project directory (default: current directory)")
    parser.add_argument("--typecheck", action="store_true", help="Run typechecking command if detected")
    parser.add_argument("--lint", action="store_true", help="Run linting command if detected")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    detected = detect_test_commands(args.project_dir)
    results = {}

    # 1. Run tests
    test_cmd = detected.get("test")
    test_res = run_command(test_cmd, cwd=args.project_dir)
    results["test"] = test_res

    # 2. Optional typecheck
    if args.typecheck:
        type_cmd = detected.get("typecheck")
        results["typecheck"] = run_command(type_cmd, cwd=args.project_dir)

    # 3. Optional lint
    if args.lint:
        lint_cmd = detected.get("lint")
        results["lint"] = run_command(lint_cmd, cwd=args.project_dir)

    all_passed = all(r.get("status") == "passed" for r in results.values() if r.get("command"))

    if args.json:
        results["overall_status"] = "passed" if all_passed else "failed"
        print(json.dumps(results, indent=2))
    else:
        print("\n🔍 dev-kit Test Verification Report")
        print("=" * 45)
        for stage, res in results.items():
            icon = "✅" if res["status"] == "passed" else ("⚠️" if res["status"] == "not_configured" else "❌")
            print(f"{icon} {stage.upper()}: {res['command'] or 'None'} -> {res['status'].upper()}")
            if res["status"] == "failed":
                print("\n--- Failure Output ---")
                if res["stdout"]:
                    print(res["stdout"].strip())
                if res["stderr"]:
                    print(res["stderr"].strip())
                print("----------------------\n")
        print("=" * 45)
        if all_passed:
            print("🎉 Quality Gate: PASSED. All tests green.\n")
        else:
            print("🛑 Quality Gate: FAILED. Fix errors before proceeding.\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
