#!/usr/bin/env python3
"""
Test Runner - Pre-commit 测试运行器
支持多种测试框架: pytest, unittest, tox
"""
import argparse
import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional


class TestRunner:
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.results: Dict[str, Any] = {
            "passed": [],
            "failed": [],
            "skipped": [],
            "errors": []
        }
    
    def detect_test_framework(self) -> str:
        """检测项目使用的测试框架"""
        if (self.project_root / "pytest.ini").exists():
            return "pytest"
        if (self.project_root / "setup.cfg").exists():
            content = (self.project_root / "setup.cfg").read_text()
            if "[tool:pytest]" in content:
                return "pytest"
        if (self.project_root / "pyproject.toml").exists():
            content = (self.project_root / "pyproject.toml").read_text()
            if "[tool.pytest" in content:
                return "pytest"
        if (self.project_root / "tox.ini").exists():
            return "tox"
        if (self.project_root / "tests").exists() or (self.project_root / "test").exists():
            return "pytest"  # 默认使用 pytest
        return "none"
    
    def run_pytest(self, args: List[str]) -> Dict[str, Any]:
        """运行 pytest 测试"""
        cmd = ["pytest", "-v", "--tb=short", "--json-report", "--json-report-file=/tmp/pytest_report.json"]
        cmd.extend(args)
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=self.project_root
            )
            
            # 尝试读取 JSON 报告
            report_file = Path("/tmp/pytest_report.json")
            if report_file.exists():
                with open(report_file) as f:
                    return json.load(f)
            
            # 解析文本输出
            return self._parse_pytest_output(result.stdout, result.stderr, result.returncode)
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": "pytest not found. Please install: pip install pytest",
                "output": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": ""
            }
    
    def _parse_pytest_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """解析 pytest 文本输出"""
        result = {
            "success": returncode == 0,
            "returncode": returncode,
            "output": stdout + stderr,
            "summary": {}
        }
        
        # 提取摘要信息
        for line in stdout.split('\n'):
            if 'passed' in line.lower():
                result["summary"]["passed"] = line.strip()
            elif 'failed' in line.lower():
                result["summary"]["failed"] = line.strip()
            elif 'skipped' in line.lower():
                result["summary"]["skipped"] = line.strip()
        
        return result
    
    def run_unittest(self, args: List[str]) -> Dict[str, Any]:
        """运行 unittest 测试"""
        cmd = ["python", "-m", "unittest", "discover"]
        cmd.extend(args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "output": result.stdout + result.stderr,
                "summary": {}
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": ""
            }
    
    def run_tox(self, args: List[str]) -> Dict[str, Any]:
        """运行 tox 测试"""
        cmd = ["tox"]
        cmd.extend(args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "output": result.stdout + result.stderr,
                "summary": {}
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "tox not found. Please install: pip install tox",
                "output": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": ""
            }
    
    def run_tests(self, framework: Optional[str] = None, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """运行测试"""
        if args is None:
            args = []
        
        if framework is None:
            framework = self.detect_test_framework()
        
        if framework == "none":
            return {
                "success": True,
                "message": "No test framework detected, skipping tests",
                "framework": "none"
            }
        
        if framework == "pytest":
            return self.run_pytest(args)
        elif framework == "unittest":
            return self.run_unittest(args)
        elif framework == "tox":
            return self.run_tox(args)
        else:
            return {
                "success": False,
                "error": f"Unknown test framework: {framework}",
                "framework": framework
            }


def main():
    parser = argparse.ArgumentParser(description="Test Runner - Pre-commit 测试运行器")
    parser.add_argument("--framework", choices=["pytest", "unittest", "tox", "auto"], default="auto")
    parser.add_argument("--output", choices=["json", "text"], default="text")
    parser.add_argument("args", nargs="*", default=[])
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # 检测或使用指定的框架
    framework = args.framework if args.framework != "auto" else runner.detect_test_framework()
    
    if framework == "auto":
        framework = runner.detect_test_framework()
    
    # 运行测试
    result = runner.run_tests(framework=framework, args=args.args)
    
    # 输出结果
    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        if result.get("success"):
            print(f"✅ Tests passed ({framework})")
            if result.get("summary"):
                for key, value in result["summary"].items():
                    print(f"   {value}")
        else:
            print(f"❌ Tests failed ({framework})", file=sys.stderr)
            if result.get("error"):
                print(f"   Error: {result['error']}", file=sys.stderr)
            if result.get("output"):
                print(result["output"][:500], file=sys.stderr)  # 限制输出长度
    
    sys.exit(0 if result.get("success", False) else 1)


if __name__ == "__main__":
    main()
