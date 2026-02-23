#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any

from hooks import BaseHook, HookResult, hook


# Patterns that indicate potential issues
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


def detect_language(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext in ['.py']:
        return 'python'
    elif ext in ['.js', '.jsx']:
        return 'javascript'
    elif ext in ['.ts', '.tsx']:
        return 'typescript'
    return None


def analyze_file(file_path: str) -> Dict[str, List[str]]:
    """Perform static analysis on a single file."""
    warnings = []
    suggestions = []
    
    try:
        content = Path(file_path).read_text()
        lang = detect_language(file_path)
        
        if not lang or lang not in SUSPICIOUS_PATTERNS:
            return {"warnings": [], "suggestions": []}
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, message in SUSPICIOUS_PATTERNS.get(lang, []):
                if re.search(pattern, line):
                    warnings.append(f"{file_path}:{i}: {message}")
                    
    except Exception as e:
        suggestions.append(f"Could not analyze {file_path}: {str(e)}")
    
    return {"warnings": warnings, "suggestions": suggestions}


def analyze_with_llm(files: List[str], audit_level: str = "standard") -> Dict[str, Any]:
    """Analyze code files for potential issues.
    
    This implementation performs static analysis. For LLM-based analysis,
    configure an API endpoint via environment variables.
    """
    all_warnings = []
    all_suggestions = []
    
    # Check for LLM configuration
    llm_endpoint = os.environ.get("LLM_ENDPOINT") or os.environ.get("OPENAI_API_KEY")
    if not llm_endpoint:
        all_suggestions.append(
            "Audit: LLM integration not configured. Set LLM_ENDPOINT or OPENAI_API_KEY for AI-powered analysis. Currently using static analysis only."
        )
    
    for file_path in files:
        if not file_path:
            continue
        
        # Skip binary files and directories
        if not Path(file_path).exists() or Path(file_path).is_dir():
            continue
            
        result = analyze_file(file_path)
        all_warnings.extend(result.get("warnings", []))
        all_suggestions.extend(result.get("suggestions", []))
    
    # Filter based on audit level
    if audit_level == "lax":
        all_warnings = []
    
    return {
        "blocking": [],
        "warnings": all_warnings,
        "suggestions": all_suggestions
    }


def get_staged_files() -> List[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return [f for f in result.stdout.strip().split("\n") if f]
    except Exception:
        return []


@hook(enabled=True, timeout=120)
class AuditHook(BaseHook):
    name = "audit"
    description = "Code review agent for logic and quality"
    
    def setup_parser(self, parser: argparse.ArgumentParser):
        parser.add_argument("--mode", choices=["shadow", "full"], default="shadow")
        parser.add_argument("--level", choices=["lax", "standard", "strict"], default="standard")
        parser.add_argument("--files", nargs="*", default=[])
    
    def run(self, context: Dict[str, Any]) -> HookResult:
        mode = self.config.get("mode", "shadow")
        level = self.config.get("level", "standard")
        exclude = self.config.get("exclude", [])
        
        files = context.get("changed_files", [])
        if not files:
            files = get_staged_files()
        
        if exclude:
            files = [f for f in files if not any(
                Path(f).match(pattern) for pattern in exclude
            )]
        
        results = analyze_with_llm(files, level)
        
        if results["blocking"]:
            return HookResult(
                name=self.name,
                success=False,
                blocking=results["blocking"],
                warnings=results["warnings"]
            )
        
        return HookResult(
            name=self.name,
            success=True,
            warnings=results["warnings"],
            suggestions=results["suggestions"]
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit Hook")
    parser.add_argument("--mode", choices=["shadow", "full"], default="shadow")
    parser.add_argument("--level", choices=["lax", "standard", "strict"], default="standard")
    parser.add_argument("--files", nargs="*", default=[])
    args = parser.parse_args()
    
    hook_instance = AuditHook({
        "mode": args.mode,
        "level": args.level,
        "files": args.files
    })
    result = hook_instance.run({})
    
    if result.blocking:
        print(f"Found {len(result.blocking)} blocking issues:", file=sys.stderr)
        for issue in result.blocking:
            print(f"  - {issue}", file=sys.stderr)
        sys.exit(1)
    
    if result.warnings:
        print(f"Warnings ({len(result.warnings)}):", file=sys.stderr)
        for w in result.warnings:
            print(f"  - {w}", file=sys.stderr)
    
    print("Audit completed")
    sys.exit(0)
