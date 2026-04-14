from __future__ import annotations

from typing import Any

INSTALLABLE_SKILLS: list[dict[str, Any]] = [
    {
        "name": "validate",
        "description": "验证项目治理规则",
        "checked": True,
        "requires_cli": [],
        "template_dir": None,
        "hooks": ["pre-commit"],
        "hook_cmd": "python3 -m nano_coding.cli validate .",
    },
    {
        "name": "principle-review",
        "description": "审查原则合规性",
        "checked": True,
        "requires_cli": [],
        "template_dir": None,
        "hooks": [],
        "hook_cmd": None,
    },
    {
        "name": "scan",
        "description": "对项目运行安全和审计扫描",
        "checked": False,
        "requires_cli": [],
        "template_dir": None,
        "hooks": ["pre-commit"],
        "hook_cmd": "python3 -m nano_coding.cli scan --path .",
    },
    {
        "name": "beads",
        "description": "AI-native issue tracking via Beads CLI",
        "checked": False,
        "requires_cli": ["bd"],
        "template_dir": "optional_skills/beads",
        "hooks": [],
        "hook_cmd": None,
    },
]

EXTERNAL_TOOLS: list[dict[str, str]] = [
    {"name": "opencode", "description": "OpenCode CLI (opencode)"},
    {"name": "pi", "description": "pi.dev CLI (pi)"},
    {"name": "openclaw", "description": "OpenClaw CLI (openclaw)"},
]
