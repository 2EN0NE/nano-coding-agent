import json
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

AUDIT_RULES = {
    "python": "python-security",
    "typescript": "ts-security",
    "go": "go-security",
    "rust": "rust-security",
}

SUSPICIOUS_PATTERNS = {
    "python": [
        (r"print\s*\(", "Print statement found - consider using logging"),
        (r"TODO\b", "TODO comment found"),
        (r"FIXME\b", "FIXME comment found"),
        (r"except:\s*\n\s*pass", "Bare except clause with pass"),
        (r"os\.environ\.get\(['\"](API_KEY|SECRET|PASSWORD|TOKEN)", "Potential secret in environment access"),
    ],
    "javascript": [
        (r"console\.log\s*\(", "Console.log found"),
        (r"TODO\b", "TODO comment found"),
        (r"FIXME\b", "FIXME comment found"),
    ],
    "typescript": [
        (r"console\.log\s*\(", "Console.log found"),
        (r"TODO\b", "TODO comment found"),
        (r"FIXME\b", "FIXME comment found"),
        (r"@ts-ignore", "ts-ignore found - may hide type errors"),
        (r"as\s+any\s*(\"|')", "Type assertion to 'any' - loses type safety"),
    ],
}


def get_rules_for_type(project_type: str) -> str:
    return AUDIT_RULES.get(project_type, "auto")


def run_semgrep(rules: str, level: str = "security") -> dict[str, Any]:
    cmd = ["semgrep", "--config", rules, "--json", "--quiet"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return json.loads(result.stdout) if result.stdout else {"results": []}
    except Exception as e:
        return {"results": [], "error": str(e)}


def filter_blocking(results: dict[str, Any]) -> list[dict[str, Any]]:
    blocking = []
    for r in results.get("results", []):
        if r.get("extra", {}).get("severity") in ["ERROR", "WARNING"]:
            blocking.append(r)
    return blocking


def detect_language(file_path: str) -> Optional[str]:
    ext = Path(file_path).suffix.lower()
    if ext in [".py"]:
        return "python"
    elif ext in [".js", ".jsx"]:
        return "javascript"
    elif ext in [".ts", ".tsx"]:
        return "typescript"
    return None


def analyze_file(file_path: str) -> dict[str, list[str]]:
    warnings: list[str] = []
    suggestions: list[str] = []
    try:
        content = Path(file_path).read_text()
        lang = detect_language(file_path)
        if not lang or lang not in SUSPICIOUS_PATTERNS:
            return {"warnings": [], "suggestions": []}
        for pattern, message in SUSPICIOUS_PATTERNS.get(lang, []):
            for match in re.finditer(pattern, content):
                line_num = content[: match.start()].count("\n") + 1
                warnings.append(f"{file_path}:{line_num}: {message}")
    except Exception as e:
        suggestions.append(f"Could not analyze {file_path}: {str(e)}")
    return {"warnings": warnings, "suggestions": suggestions}


def get_staged_files() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return [f for f in result.stdout.strip().split("\n") if f]
    except Exception:
        return []


def run_security_scan(project_type: str = "auto") -> dict:
    rules = get_rules_for_type(project_type)
    results = run_semgrep(rules)
    blocking_results = filter_blocking(results)
    blocking: list[str] = []
    for r in blocking_results:
        path = r.get("path", "")
        start = r.get("start", {})
        line = start.get("line", "") if isinstance(start, dict) else ""
        msg = r.get("extra", {}).get("message", "")
        blocking.append(f"{path}:{line}: {msg}")
    warnings: list[str] = []
    suggestions: list[str] = []
    if "error" in results:
        warnings.append(f"Security scan warning: {results['error']}")
    return {"blocking": blocking, "warnings": warnings, "suggestions": suggestions}


def run_audit_scan(
    files: Optional[list[str]] = None,
    level: str = "standard",
    exclude: Optional[list[str]] = None,
) -> dict:
    if not files:
        files = get_staged_files()
    if exclude is None:
        exclude = []
    filtered_files = [f for f in files if not any(exc in f for exc in exclude)]
    blocking: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []
    for f in filtered_files:
        analysis = analyze_file(f)
        warnings.extend(analysis.get("warnings", []))
        suggestions.extend(analysis.get("suggestions", []))
    return {"blocking": blocking, "warnings": warnings, "suggestions": suggestions}
