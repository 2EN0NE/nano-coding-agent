#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum


class CheckStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str
    details: List[str] = field(default_factory=list)
    duration: float = 0.0
    
    def __post_init__(self):
        if self.details is None:
            self.details = []


class UnifiedReporter:
    COLORS = {
        "reset": "\033[0m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "bold": "\033[1m",
    }
    
    def __init__(self, use_color: bool = True):
        self.use_color = use_color and sys.stdout.isatty()
        self.results: List[CheckResult] = []
    
    def _color(self, text: str, color: str) -> str:
        if not self.use_color:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"
    
    def _format_status(self, status: CheckStatus) -> str:
        symbols = {
            CheckStatus.PASSED: "✓",
            CheckStatus.FAILED: "✗",
            CheckStatus.WARNING: "⚠",
            CheckStatus.SKIPPED: "○",
            CheckStatus.ERROR: "✗",
        }
        colors = {
            CheckStatus.PASSED: "green",
            CheckStatus.FAILED: "red",
            CheckStatus.WARNING: "yellow",
            CheckStatus.SKIPPED: "cyan",
            CheckStatus.ERROR: "red",
        }
        symbol = symbols.get(status, "?")
        color = colors.get(status, "white")
        return self._color(f"[{symbol}]", color)
    
    def add_result(self, result: CheckResult):
        self.results.append(result)
    
    def add_check(self, name: str, status: CheckStatus, message: str = "", details: List[str] = [], duration: float = 0.0):
        result = CheckResult(
            name=name,
            status=status,
            message=message,
            details=details,
            duration=duration
        )
        self.results.append(result)
    
    def print_header(self, title: str):
        width = 60
        print()
        print(self._color("=" * width, "cyan"))
        print(self._color(f"  {title}", "bold"))
        print(self._color("=" * width, "cyan"))
    
    def print_check(self, result: CheckResult):
        status_str = self._format_status(result.status)
        name_str = self._color(result.name, "bold")
        
        if result.status == CheckStatus.PASSED:
            print(f"  {status_str} {name_str}")
        elif result.status == CheckStatus.SKIPPED:
            print(f"  {status_str} {name_str} {self._color('(skipped)', 'cyan')}")
        else:
            print(f"  {status_str} {name_str}")
            if result.message:
                print(f"      {self._color(result.message, 'white')}")
            for detail in result.details:
                print(f"        • {detail}")
        
        if result.duration > 0:
            print(f"      {self._color(f'[{result.duration:.2f}s]', 'cyan')}")
    
    def print_summary(self):
        passed = sum(1 for r in self.results if r.status == CheckStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAILED)
        warnings = sum(1 for r in self.results if r.status == CheckStatus.WARNING)
        skipped = sum(1 for r in self.results if r.status == CheckStatus.SKIPPED)
        errors = sum(1 for r in self.results if r.status == CheckStatus.ERROR)
        
        total = len(self.results)
        
        print()
        print(self._color("-" * 60, "cyan"))
        
        summary_parts = []
        if passed > 0:
            summary_parts.append(self._color(f"{passed} passed", "green"))
        if failed > 0:
            summary_parts.append(self._color(f"{failed} failed", "red"))
        if warnings > 0:
            summary_parts.append(self._color(f"{warnings} warnings", "yellow"))
        if skipped > 0:
            summary_parts.append(self._color(f"{skipped} skipped", "cyan"))
        if errors > 0:
            summary_parts.append(self._color(f"{errors} errors", "red"))
        
        print(f"  {' | '.join(summary_parts)}")
        print(self._color("-" * 60, "cyan"))
        
        return failed == 0 and errors == 0
    
    def print_json(self) -> str:
        data = {
            "results": [asdict(r) for r in self.results],
            "summary": {
                "passed": sum(1 for r in self.results if r.status == CheckStatus.PASSED),
                "failed": sum(1 for r in self.results if r.status == CheckStatus.FAILED),
                "warnings": sum(1 for r in self.results if r.status == CheckStatus.WARNING),
                "skipped": sum(1 for r in self.results if r.status == CheckStatus.SKIPPED),
                "errors": sum(1 for r in self.results if r.status == CheckStatus.ERROR),
            }
        }
        return json.dumps(data, indent=2)
    
    def render(self, title: str = "Pre-commit Checks") -> bool:
        self.print_header(title)
        
        for result in self.results:
            self.print_check(result)
        
        return self.print_summary()


def load_results_from_file(filepath: str) -> Dict[str, Any]:
    path = Path(filepath)
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


def run_checks_from_config(checks: List[Dict[str, Any]]) -> UnifiedReporter:
    reporter = UnifiedReporter()
    
    for check in checks:
        name = check.get("name", "Unknown")
        command = check.get("command", "")
        
        if not command:
            reporter.add_check(name, CheckStatus.SKIPPED, "No command specified")
            continue
        
        import subprocess
        import time
        
        start = time.time()
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=check.get("timeout", 300)
            )
            duration = time.time() - start
            
            if result.returncode == 0:
                status = CheckStatus.PASSED
                message = "Check passed"
            else:
                status = CheckStatus.FAILED
                output = result.stderr or result.stdout
                message = output[:200] if output else "Check failed"
            
            reporter.add_check(name, status, message, duration=duration)
            
        except subprocess.TimeoutExpired:
            reporter.add_check(name, CheckStatus.ERROR, f"Timeout after {check.get('timeout', 300)}s", duration=time.time() - start)
        except Exception as e:
            reporter.add_check(name, CheckStatus.ERROR, str(e), duration=time.time() - start)
    
    return reporter


def main():
    parser = argparse.ArgumentParser(description="Unified Reporter - Pre-commit 结果聚合显示")
    parser.add_argument("--title", default="Pre-commit Checks", help="Report title")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--config", help="JSON config file for checks")
    parser.add_argument("--result-file", help="Load results from file")
    args = parser.parse_args()
    
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
        reporter = run_checks_from_config(config.get("checks", []))
    else:
        reporter = UnifiedReporter()
    
    if args.json:
        print(reporter.print_json())
    else:
        success = reporter.render(args.title)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
