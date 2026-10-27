#!/usr/bin/env bash
# dev-kit installer
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Support both:
#   install.sh [target_dir] [tool]
#   install.sh [tool]  (e.g. install.sh antigravity)
if [[ "${1:-}" =~ ^(claude|antigravity|cursor|all)$ ]]; then
    TOOL="$1"
    TARGET_DIR="${2:-.}"
else
    TARGET_DIR="${1:-.}"
    TOOL="${2:-all}"
fi

echo "🚀 Installing dev-kit adapters into: $TARGET_DIR"

install_claude() {
    mkdir -p "$TARGET_DIR/.claude/commands"
    cp "$KIT_DIR/adapters/claude/commands/"*.md "$TARGET_DIR/.claude/commands/"
    echo "  ✓ Claude Code commands installed: /dev, /dev-feature, /dev-qa"
}

install_antigravity() {
    mkdir -p "$TARGET_DIR/.agents/skills/dev"
    mkdir -p "$TARGET_DIR/.agents/skills/dev-feature"
    mkdir -p "$TARGET_DIR/.agents/skills/dev-qa"
    cp "$KIT_DIR/adapters/antigravity/skills/dev/SKILL.md" "$TARGET_DIR/.agents/skills/dev/"
    cp "$KIT_DIR/adapters/antigravity/skills/dev-feature/SKILL.md" "$TARGET_DIR/.agents/skills/dev-feature/"
    cp "$KIT_DIR/adapters/antigravity/skills/dev-qa/SKILL.md" "$TARGET_DIR/.agents/skills/dev-qa/"
    echo "  ✓ Antigravity skills installed: dev, dev-feature, dev-qa"
}

install_cursor() {
    mkdir -p "$TARGET_DIR/.cursor/rules"
    cp "$KIT_DIR/adapters/cursor/rules/dev.mdc" "$TARGET_DIR/.cursor/rules/"
    echo "  ✓ Cursor rules installed: .cursor/rules/dev.mdc"
}

case "$TOOL" in
    claude) install_claude ;;
    antigravity) install_antigravity ;;
    cursor) install_cursor ;;
    all)
        install_claude
        install_antigravity
        install_cursor
        ;;
    *)
        echo "Unknown tool: $TOOL (use claude, antigravity, cursor, or all)" >&2
        exit 1
        ;;
esac

echo "✅ dev-kit installation complete!"
