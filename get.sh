#!/usr/bin/env bash
# dev-kit one-line installer
set -euo pipefail

DEV_KIT_REF="${DEV_KIT_REF:-main}"

# Support both:
#   get.sh [target_dir] [tool]
#   get.sh [tool]  (e.g. bash -s -- antigravity)
if [[ "${1:-}" =~ ^(claude|antigravity|cursor|all)$ ]]; then
    TOOL="$1"
    TARGET_DIR="${2:-.}"
else
    TARGET_DIR="${1:-.}"
    TOOL="${2:-all}"
fi

echo "📦 Downloading dev-kit ($DEV_KIT_REF)..."
mkdir -p "$TARGET_DIR/dev-kit"

ARCHIVE_URL="https://github.com/victorfigueira/dev-kit/archive/${DEV_KIT_REF}.tar.gz"

if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$ARCHIVE_URL" | tar -xz -C "$TARGET_DIR/dev-kit" --strip-components=1
elif command -v wget >/dev/null 2>&1; then
    wget -qO- "$ARCHIVE_URL" | tar -xz -C "$TARGET_DIR/dev-kit" --strip-components=1
else
    echo "Error: curl or wget is required." >&2
    exit 1
fi

echo "🔧 Running dev-kit installer..."
bash "$TARGET_DIR/dev-kit/install.sh" "$TARGET_DIR" "$TOOL"
