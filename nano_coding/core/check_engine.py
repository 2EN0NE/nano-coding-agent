from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class Issue:
    path: str | None
    line: int | None
    rule_id: str
    message: str
    principle: str
    practice: str
    severity: Literal["blocking", "warning"]


class Check:
    name: str
    principle: str
    practice: str
    requires_llm: bool = False
    severity: Literal["blocking", "warning"] = "blocking"

    def run(self, project_root: Path) -> list[Issue]:
        raise NotImplementedError


class CheckEngine:
    def __init__(self) -> None:
        self._checks: dict[str, Check] = {}

    def register(self, check: Check) -> None:
        self._checks[check.name] = check

    def run_all(
        self,
        project_root: Path,
        names: list[str] | None = None,
        llm: bool = False,
    ) -> dict[str, list[Issue]]:
        results: dict[str, list[Issue]] = {}
        for name, check in self._checks.items():
            if names is not None and name not in names:
                continue
            if check.requires_llm and not llm:
                continue
            results[name] = check.run(project_root)
        return results
