#!/bin/bash
set -e

BEADS_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

echo "=== Beads Skill Installer ==="
echo "Project: $PROJECT_ROOT"
echo ""

check_bd() {
    if ! command -v bd &> /dev/null; then
        echo "❌ bd CLI not found"
        echo ""
        echo "Install with:"
        echo "  curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash"
        echo ""
        echo "Or use one of:"
        echo "  npm install -g @beads/bd"
        echo "  brew install beads"
        echo "  go install github.com/steveyegge/beads/cmd/bd@latest"
        exit 1
    fi
    echo "✅ bd CLI found: $(bd --version)"
}

init_beads() {
    echo ""
    echo "=== Initializing Beads in project ==="
    
    if [ -d "$PROJECT_ROOT/.beads" ]; then
        echo "⚠️  Beads already initialized"
    else
        bd init
        echo "✅ Beads initialized"
    fi
}

copy_skill_scripts() {
    echo ""
    echo "=== Installing skill scripts ==="
    
    mkdir -p "$PROJECT_ROOT/scripts"
    
    if [ -f "$BEADS_SCRIPT_DIR/read_task_beads.py" ]; then
        cp "$BEADS_SCRIPT_DIR/read_task_beads.py" "$PROJECT_ROOT/scripts/"
        chmod +x "$PROJECT_ROOT/scripts/read_task_beads.py"
        echo "✅ Installed: scripts/read_task_beads.py"
    fi
    
    if [ -f "$BEADS_SCRIPT_DIR/write_task_checkpoint.py" ]; then
        cp "$BEADS_SCRIPT_DIR/write_task_checkpoint.py" "$PROJECT_ROOT/scripts/"
        chmod +x "$PROJECT_ROOT/scripts/write_task_checkpoint.py"
        echo "✅ Installed: scripts/write_task_checkpoint.py"
    fi
}

add_to_agents() {
    echo ""
    echo "=== Updating AGENTS.md ==="
    
    AGENTS_FILE="$PROJECT_ROOT/AGENTS.md"
    BEADS_NOTE="

## Beads Task Memory

Use bd (Beads) for cross-session task tracking:

- \`python scripts/read_task_beads.py --ready\` - List ready tasks
- \`python scripts/read_task_beads.py --current-branch\` - Tasks for current branch
- \`python scripts/write_task_checkpoint.py --summary "..." --next-steps "..."\` - Save checkpoint
"
    
    if [ -f "$AGENTS_FILE" ]; then
        if ! grep -q "Beads Task Memory" "$AGENTS_FILE"; then
            echo "$BEADS_NOTE" >> "$AGENTS_FILE"
            echo "✅ Updated AGENTS.md"
        else
            echo "ℹ️  AGENTS.md already contains Beads info"
        fi
    else
        echo "$BEADS_NOTE" > "$AGENTS_FILE"
        echo "✅ Created AGENTS.md"
    fi
}

main() {
    check_bd
    init_beads
    copy_skill_scripts
    add_to_agents
    
    echo ""
    echo "=== Installation complete ==="
    echo ""
    echo "Usage:"
    echo "  # Read task memory"
    echo "  python scripts/read_task_beads.py --ready"
    echo "  python scripts/read_task_beads.py --current-branch"
    echo "  python scripts/read_task_beads.py --task-id bd-xxx"
    echo ""
    echo "  # Save checkpoint before ending session"
    echo "  python scripts/write_task_checkpoint.py \\"
    echo "    --summary \"Completed auth refactoring, fixed login flow\" \\"
    echo "    --next-steps \"Connect frontend to new API, update tests\""
    echo ""
    echo "  # Or update specific task"
    echo "  python scripts/write_task_checkpoint.py \\"
    echo "    --task-id bd-xxx \\"
    echo "    --summary \"...\" \\"
    echo "    --next-steps \"...\""
}

main "$@"
