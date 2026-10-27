#!/usr/bin/env python3
"""Version checking and update utility for dev-kit.

Checks GitHub for newer versions of dev-kit and, only when asked, installs them.
The agent follows dev-kit/UPDATE.md and asks the user before running `update`.

Usage:
  python3 dev-kit/tools/updater.py check [--json]
  python3 dev-kit/tools/updater.py update [--tool TOOL] [--target-dir DIR]
"""
import argparse
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request


def safe_urlopen(req, timeout=10):
    """Execute urllib request with fallback for environments with SSL certificate verification issues."""
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e) or "certificate verify failed" in str(e).lower():
            ctx = ssl._create_unverified_context()
            return urllib.request.urlopen(req, timeout=timeout, context=ctx)
        raise

REPO_RAW_VERSION = "https://raw.githubusercontent.com/victorfigueira/dev-kit/main/VERSION"
REPO_RAW_CHANGELOG = "https://raw.githubusercontent.com/victorfigueira/dev-kit/main/CHANGELOG.md"
REPO_API_TAGS = "https://api.github.com/repos/victorfigueira/dev-kit/tags"
REPO_ARCHIVE_URL = "https://github.com/victorfigueira/dev-kit/archive/refs/heads/main.tar.gz"


def find_dev_kit_dir():
    """Locate the dev-kit directory whether invoked from root or inside dev-kit."""
    current_dir = os.path.abspath(os.getcwd())

    # Case 1: Running in consumer project with ./dev-kit
    if os.path.exists(os.path.join(current_dir, "dev-kit", "VERSION")):
        return os.path.join(current_dir, "dev-kit")

    # Case 2: Running directly inside dev-kit repo
    if os.path.exists(os.path.join(current_dir, "VERSION")) and os.path.exists(os.path.join(current_dir, "install.sh")):
        return current_dir

    # Case 3: Script path relative
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    if os.path.exists(os.path.join(parent_dir, "VERSION")):
        return parent_dir

    return None


def read_local_version(dev_kit_dir=None):
    """Read local version string from VERSION file."""
    base_dir = dev_kit_dir or find_dev_kit_dir()
    if not base_dir:
        return "0.0.0"

    version_path = os.path.join(base_dir, "VERSION")
    if os.path.exists(version_path):
        try:
            with open(version_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return "0.0.0"
    return "0.0.0"


def parse_semver(version_str):
    """Parse version string into (major, minor, patch) integer tuple."""
    clean = re.sub(r"^v", "", version_str.strip())
    parts = clean.split(".")
    try:
        return tuple(int(re.sub(r"\D", "", p)) for p in parts[:3])
    except (ValueError, IndexError):
        return (0, 0, 0)


def is_newer(remote_version, local_version):
    """Return True if remote_version is strictly newer than local_version."""
    remote_parts = parse_semver(remote_version)
    local_parts = parse_semver(local_version)
    return remote_parts > local_parts


def fetch_remote_version(timeout=4):
    """Fetch latest version from GitHub raw file or tags API with timeout."""
    # 1. Try raw VERSION file on main (fast, no rate limits)
    req = urllib.request.Request(
        REPO_RAW_VERSION,
        headers={"User-Agent": "dev-kit-updater"}
    )
    try:
        with safe_urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8").strip()
            if content and re.match(r"^\d+\.\d+\.\d+", content):
                return content
    except Exception:
        pass

    # 2. Fallback to GitHub Tags API
    api_req = urllib.request.Request(
        REPO_API_TAGS,
        headers={"User-Agent": "dev-kit-updater"}
    )
    try:
        with safe_urlopen(api_req, timeout=timeout) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
            if tags and isinstance(tags, list):
                top_tag = tags[0].get("name", "")
                return re.sub(r"^v", "", top_tag)
    except Exception:
        pass

    return None


def fetch_remote_changelog(timeout=4):
    """Fetch the latest CHANGELOG.md from GitHub, or None if unreachable."""
    req = urllib.request.Request(REPO_RAW_CHANGELOG, headers={"User-Agent": "dev-kit-updater"})
    try:
        with safe_urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None


def changelog_since(changelog_text, local_version):
    """Return the changelog entries newer than local_version, newest first."""
    entries = []
    current = None
    for line in (changelog_text or "").splitlines():
        header = re.match(r"^##\s+v?(\d+\.\d+\.\d+)\s*(?:[–-]\s*(.+))?$", line.strip())
        if header:
            current = {"version": header.group(1), "date": (header.group(2) or "").strip(), "notes": []}
            entries.append(current)
        elif current and line.strip().startswith("- "):
            current["notes"].append(line.strip()[2:])
    return [e for e in entries if is_newer(e["version"], local_version)]


def check_for_updates():
    """Check if an update is available, with the changelog entries it would bring."""
    local_ver = read_local_version()
    remote_ver = fetch_remote_version()

    if not remote_ver:
        return {
            "current_version": local_ver,
            "latest_version": local_ver,
            "update_available": False,
            "major_change": False,
            "changelog": [],
            "offline": True
        }

    update_needed = is_newer(remote_ver, local_ver)
    return {
        "current_version": local_ver,
        "latest_version": remote_ver,
        "update_available": update_needed,
        "major_change": update_needed and parse_semver(remote_ver)[0] > parse_semver(local_ver)[0],
        "changelog": changelog_since(fetch_remote_changelog(), local_ver) if update_needed else [],
        "offline": False
    }


def is_kit_source_repo(project_root):
    """True when project_root is the dev-kit source repository, not a project that uses it."""
    return (os.path.exists(os.path.join(project_root, "install.sh"))
            and os.path.exists(os.path.join(project_root, "VERSION"))
            and not os.path.exists(os.path.join(project_root, "dev-kit", "VERSION")))


def perform_update(target_dir=None, tool="all"):
    """Download latest dev-kit package and run installer."""
    project_root = target_dir or os.getcwd()
    target_dev_kit = os.path.join(project_root, "dev-kit")

    if is_kit_source_repo(project_root):
        print("This is the dev-kit source repository; update it with git instead.", file=sys.stderr)
        return False

    # Standard consumer installation: download tarball
    print(f"📦 Downloading latest dev-kit into {target_dev_kit}...")
    try:
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_tar:
            tmp_path = tmp_tar.name

        req = urllib.request.Request(REPO_ARCHIVE_URL, headers={"User-Agent": "dev-kit-updater"})
        with safe_urlopen(req, timeout=15) as resp:
            with open(tmp_path, "wb") as f:
                shutil.copyfileobj(resp, f)

        os.makedirs(target_dev_kit, exist_ok=True)
        with tarfile.open(tmp_path, "r:gz") as tar:
            members = tar.getmembers()
            # Find common prefix to strip root folder
            common_prefix = os.path.commonpath([m.name for m in members if m.name])
            for member in members:
                if member.name == common_prefix:
                    continue
                member.name = os.path.relpath(member.name, common_prefix)
                tar.extract(member, path=target_dev_kit)

        os.remove(tmp_path)

        # Run installer
        install_script = os.path.join(target_dev_kit, "install.sh")
        if os.path.exists(install_script):
            subprocess.run(["bash", install_script, project_root, tool], check=True)

        new_version = read_local_version(target_dev_kit)
        print(f"✅ dev-kit updated successfully to v{new_version}!")
        return True

    except Exception as e:
        print(f"Error updating dev-kit: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="dev-kit update and version management.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Check
    check_p = subparsers.add_parser("check", help="Check for newer dev-kit version")
    check_p.add_argument("--json", action="store_true", help="Output JSON format")

    # Update
    update_p = subparsers.add_parser("update", help="Update dev-kit to latest version")
    update_p.add_argument("--tool", default="all", help="Target tool (claude, antigravity, cursor, all)")
    update_p.add_argument("--target-dir", default=None, help="Root directory of consumer project")

    args = parser.parse_args()

    if args.command == "check":
        status = check_for_updates()
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            if status["offline"]:
                print(f"dev-kit v{status['current_version']} (Offline / Could not check for updates)")
            elif status["update_available"]:
                print(f"🔔 Update available: v{status['current_version']} ➔ v{status['latest_version']}")
                for entry in status["changelog"]:
                    print(f"  {entry['version']}: " + " ".join(entry["notes"]))
            else:
                print(f"✅ dev-kit is up to date (v{status['current_version']})")
        return 0

    elif args.command == "update":
        success = perform_update(target_dir=args.target_dir, tool=args.tool)
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
