import json
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

from nano_coding.core.config_loader import resolve_config

DEFAULT_SCAN_TOOLS = ["semgrep", "regex"]


def _is_inside_string(line: str, pos: int) -> bool:
    in_single = False
    in_double = False
    escaped = False
    for i, char in enumerate(line):
        if i > pos:
            break
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"' and not in_single:
            in_double = not in_double
        elif char == "'" and not in_double:
            in_single = not in_single
    return in_single or in_double


def _get_default_suspicious_patterns() -> dict[str, list[tuple[str, str]]]:
    return {
        "python": [
            (r"print\s*\(", "Print statement found - consider using logging"),
            (r"#.*TODO\b", "TODO comment found"),
            (r"#.*FIXME\b", "FIXME comment found"),
            (
                r"except:\s*\n\s*pass",
                "Bare except clause with pass",
            ),
            (
                r"os\.environ\.get\(['\"](API_KEY|SECRET|PASSWORD|TOKEN)",
                "Potential secret in environment access",
            ),
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
            (
                r"as\s+any\s*(\"|')",
                "Type assertion to 'any' - loses type safety",
            ),
        ],
    }


def _get_default_audit_rules() -> dict[str, str]:
    return {
        "python": "python-security",
        "typescript": "ts-security",
        "go": "go-security",
        "rust": "rust-security",
    }


def _get_scan_config(target_dir: Optional[str] = None) -> dict:
    config = resolve_config(Path(target_dir) if target_dir else None)
    return config.get("scan", {})


def _load_extra_patterns(rule_paths: list[str]) -> dict[str, list[tuple[str, str]]]:
    patterns: dict[str, list[tuple[str, str]]] = {}
    for path_str in rule_paths:
        path = Path(path_str)
        if not path.exists():
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                continue
            for lang, lang_patterns in data.items():
                if not isinstance(lang_patterns, list):
                    continue
                if lang not in patterns:
                    patterns[lang] = []
                for p in lang_patterns:
                    if isinstance(p, (list, tuple)) and len(p) >= 2:
                        patterns[lang].append((str(p[0]), str(p[1])))
        except Exception:
            continue
    return patterns


def get_rules_for_type(project_type: str, scan_config: dict | None = None) -> str:
    audit_rules = _get_default_audit_rules()
    if scan_config and isinstance(scan_config.get("audit_rules"), dict):
        audit_rules.update(scan_config["audit_rules"])
    return audit_rules.get(project_type, "auto")


def run_semgrep(
    rules: str, level: str = "security", extra_rules: Optional[list[str]] = None
) -> dict[str, Any]:
    cmd = ["semgrep", "--config", rules, "--json", "--quiet"]
    for r in extra_rules or []:
        cmd.extend(["--config", r])
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


def detect_language(
    file_path: str, ext_map: dict[str, list[str]] | None = None
) -> Optional[str]:
    if ext_map is None:
        ext_map = {
            "python": [".py"],
            "javascript": [".js", ".jsx"],
            "typescript": [".ts", ".tsx"],
        }
    ext = Path(file_path).suffix.lower()
    for lang, exts in ext_map.items():
        if ext in exts:
            return lang
    return None


def analyze_file(
    file_path: str,
    patterns: Optional[dict[str, list[tuple[str, str]]]] = None,
    ext_map: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    warnings: list[str] = []
    suggestions: list[str] = []
    if patterns is None:
        patterns = _get_default_suspicious_patterns()
    try:
        content = Path(file_path).read_text()
        lang = detect_language(file_path, ext_map=ext_map)
        if not lang or lang not in patterns:
            return {"warnings": [], "suggestions": []}
        for pattern, message in patterns.get(lang, []):
            for match in re.finditer(pattern, content):
                line_num = content[: match.start()].count("\n") + 1
                line_content = content.split("\n")[line_num - 1]
                line_start = content.rfind("\n", 0, match.start()) + 1
                pos_in_line = match.start() - line_start
                if _is_inside_string(line_content, pos_in_line):
                    continue
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


def run_security_scan(
    project_type: str = "auto", target_dir: Optional[str] = None
) -> dict:
    scan_config = _get_scan_config(target_dir)
    tools = scan_config.get("tools", DEFAULT_SCAN_TOOLS)
    if "semgrep" not in tools:
        return {"blocking": [], "warnings": [], "suggestions": []}

    rules = get_rules_for_type(project_type, scan_config=scan_config)
    extra_rules = scan_config.get("rules", [])
    results = run_semgrep(rules, extra_rules=extra_rules)
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
    target_dir: Optional[str] = None,
) -> dict:
    scan_config = _get_scan_config(target_dir)
    tools = scan_config.get("tools", DEFAULT_SCAN_TOOLS)
    if "regex" not in tools:
        return {"blocking": [], "warnings": [], "suggestions": []}

    if not files:
        files = get_staged_files()
    if exclude is None:
        exclude = []
    ignore_paths = scan_config.get("ignore_paths", [])
    exclude = exclude + ignore_paths
    filtered_files = [f for f in files if not any(exc in f for exc in exclude)]

    extra_rules = scan_config.get("rules", [])
    extra_patterns = _load_extra_patterns(extra_rules)
    patterns = {
        lang: list(items) for lang, items in _get_default_suspicious_patterns().items()
    }
    config_patterns = scan_config.get("suspicious_patterns")
    if isinstance(config_patterns, dict):
        for lang, lang_patterns in config_patterns.items():
            if not isinstance(lang_patterns, list):
                continue
            parsed = []
            for p in lang_patterns:
                if isinstance(p, dict) and "pattern" in p and "message" in p:
                    parsed.append((str(p["pattern"]), str(p["message"])))
                elif isinstance(p, (list, tuple)) and len(p) >= 2:
                    parsed.append((str(p[0]), str(p[1])))
            if parsed:
                patterns.setdefault(lang, []).extend(parsed)
    for lang, lang_patterns in extra_patterns.items():
        patterns.setdefault(lang, []).extend(lang_patterns)

    ext_map = None
    config_ext_map = scan_config.get("language_extensions")
    if isinstance(config_ext_map, dict):
        ext_map = {k: list(v) for k, v in config_ext_map.items()}

    blocking: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []
    for f in filtered_files:
        analysis = analyze_file(f, patterns=patterns, ext_map=ext_map)
        warnings.extend(analysis.get("warnings", []))
        suggestions.extend(analysis.get("suggestions", []))
    return {"blocking": blocking, "warnings": warnings, "suggestions": suggestions}
