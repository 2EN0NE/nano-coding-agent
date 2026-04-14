"""SKILL.md parser: extracts YAML frontmatter and Markdown body."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n?---\s*\n(.*)$", re.DOTALL)


def parse_skill_md(content: str) -> dict[str, Any]:
    match = _FRONTMATTER_RE.match(content)
    if not match:
        raise ValueError("Missing '---' frontmatter separator")

    raw_frontmatter, body = match.group(1), match.group(2)
    frontmatter = yaml.safe_load(raw_frontmatter) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError("Frontmatter must be a YAML mapping")

    result = dict(frontmatter)
    result.setdefault("type", "markdown")
    result["body"] = body
    return result


def load_skill_from_file(path: Path) -> dict[str, Any]:
    return parse_skill_md(path.read_text(encoding="utf-8"))
