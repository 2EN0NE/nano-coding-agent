#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv &>/dev/null; then
    echo "Error: uv is not installed or not in PATH" >&2
    exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SANDBOX_DIR="$PROJECT_ROOT/.sandbox-integration"
VENV_DIR="$PROJECT_ROOT/.venv-integration"

rm -rf "$VENV_DIR"
if ! uv venv "$VENV_DIR" --python 3.11 2>/dev/null; then
    uv venv "$VENV_DIR" --python python3
fi

rm -rf "$SANDBOX_DIR"
mkdir -p "$SANDBOX_DIR"
rsync -a \
    --exclude=.venv \
    --exclude=.sandbox-integration \
    --exclude=.venv-integration \
    --exclude=.gitignore \
    --exclude=__pycache__ \
    --exclude='*.pyc' \
    "$PROJECT_ROOT/" "$SANDBOX_DIR/"

TMP_PYPROJECT="$(mktemp)"
TMP_SCRIPT="$(mktemp)"
TMP_TESTS="$(mktemp -d)"
TMP_NANO="$(mktemp -d)"
cp "$SANDBOX_DIR/pyproject.toml" "$TMP_PYPROJECT"
cp "$SANDBOX_DIR/scripts/test-integration.sh" "$TMP_SCRIPT" 2>/dev/null || true
cp -r "$SANDBOX_DIR/tests/integration" "$TMP_TESTS"
cp -r "$SANDBOX_DIR/nano_coding" "$TMP_NANO"
cp -r "$SANDBOX_DIR/principles" "$TMP_NANO" 2>/dev/null || true

cd "$SANDBOX_DIR"
git reset --hard
git clean -fd
git checkout main

cp "$TMP_PYPROJECT" "$SANDBOX_DIR/pyproject.toml"
mkdir -p "$SANDBOX_DIR/scripts"
cp "$TMP_SCRIPT" "$SANDBOX_DIR/scripts/test-integration.sh" 2>/dev/null || true
rm -rf "$SANDBOX_DIR/tests/integration" && cp -r "$TMP_TESTS/integration" "$SANDBOX_DIR/tests/integration"
rm -rf "$SANDBOX_DIR/nano_coding" && cp -r "$TMP_NANO/nano_coding" "$SANDBOX_DIR/nano_coding"
rm -rf "$SANDBOX_DIR/principles" && cp -r "$TMP_NANO/principles" "$SANDBOX_DIR/principles" 2>/dev/null || true
rm -f "$TMP_PYPROJECT" "$TMP_SCRIPT"
rm -rf "$TMP_TESTS" "$TMP_NANO"

cd "$SANDBOX_DIR"
UV_PROJECT_ENVIRONMENT="$VENV_DIR" uv pip install -e . --group integration

cd "$SANDBOX_DIR"
UV_PROJECT_ENVIRONMENT="$VENV_DIR" uv run python -c "
import shutil, os
shutil.rmtree('tests/data/temp', ignore_errors=True)
os.makedirs('tests/data/temp', exist_ok=True)
print('Environment reset')
"

cd "$SANDBOX_DIR"
UV_PROJECT_ENVIRONMENT="$VENV_DIR" uv run pytest tests/integration -v
