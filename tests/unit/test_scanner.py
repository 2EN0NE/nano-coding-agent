import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from nano_coding.core.scanner import (
    get_rules_for_type,
    run_semgrep,
    filter_blocking,
    detect_language,
    analyze_file,
    get_staged_files,
    run_security_scan,
    run_audit_scan,
)


class TestScannerHelpers(unittest.TestCase):
    def test_get_rules_for_type_python(self):
        self.assertEqual(get_rules_for_type("python"), "python-security")

    def test_get_rules_for_type_unknown(self):
        self.assertEqual(get_rules_for_type("unknown"), "auto")

    def test_filter_blocking(self):
        results = {
            "results": [
                {
                    "extra": {"severity": "INFO", "message": "info msg"},
                    "path": "a.py",
                    "start": {"line": 1},
                },
                {
                    "extra": {"severity": "ERROR", "message": "error msg"},
                    "path": "b.py",
                    "start": {"line": 2},
                },
                {
                    "extra": {"severity": "WARNING", "message": "warn msg"},
                    "path": "c.py",
                    "start": {"line": 3},
                },
            ]
        }
        blocking = filter_blocking(results)
        self.assertEqual(len(blocking), 2)
        self.assertEqual(blocking[0]["extra"]["severity"], "ERROR")
        self.assertEqual(blocking[1]["extra"]["severity"], "WARNING")

    def test_detect_language(self):
        self.assertEqual(detect_language("foo.py"), "python")
        self.assertEqual(detect_language("foo.ts"), "typescript")
        self.assertEqual(detect_language("foo.js"), "javascript")
        self.assertEqual(detect_language("foo.jsx"), "javascript")
        self.assertIsNone(detect_language("foo.rs"))

    def test_analyze_file_console_log(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write("console.log('hello');\n")
            name = f.name
        try:
            result = analyze_file(name)
            self.assertTrue(any("Console.log found" in w for w in result["warnings"]))
        finally:
            os.unlink(name)

    def test_analyze_file_todo(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# TODO: fix this\n")
            name = f.name
        try:
            result = analyze_file(name)
            self.assertTrue(any("TODO comment found" in w for w in result["warnings"]))
        finally:
            os.unlink(name)

    def test_analyze_file_bare_except(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("try:\n    pass\nexcept:\n    pass\n")
            name = f.name
        try:
            result = analyze_file(name)
            self.assertTrue(
                any("Bare except clause with pass" in w for w in result["warnings"])
            )
        finally:
            os.unlink(name)


class TestRunSecurityScan(unittest.TestCase):
    @patch("nano_coding.core.scanner.subprocess.run")
    def test_run_security_scan_success(self, mock_run):
        mock_output = json.dumps(
            {
                "results": [
                    {
                        "extra": {"severity": "ERROR", "message": "bad pattern"},
                        "path": "main.py",
                        "start": {"line": 5},
                    },
                    {
                        "extra": {"severity": "INFO", "message": "info"},
                        "path": "main.py",
                        "start": {"line": 10},
                    },
                ]
            }
        )
        mock_run.return_value = MagicMock(stdout=mock_output, stderr="")
        result = run_security_scan("python")
        self.assertEqual(len(result["blocking"]), 1)
        self.assertIn("main.py:5: bad pattern", result["blocking"])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["suggestions"], [])

    @patch("nano_coding.core.scanner.subprocess.run")
    def test_run_security_scan_missing_semgrep(self, mock_run):
        mock_run.side_effect = FileNotFoundError("semgrep not found")
        result = run_security_scan("python")
        self.assertEqual(result["blocking"], [])
        self.assertTrue(
            any("semgrep" in w.lower() for w in result["warnings"])
            or any("not found" in w.lower() for w in result["warnings"])
        )
        self.assertEqual(result["suggestions"], [])


class TestRunAuditScan(unittest.TestCase):
    def test_run_audit_scan_with_files(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write("console.log('test');\n")
            name = f.name
        try:
            result = run_audit_scan(files=[name])
            self.assertTrue(any("Console.log found" in w for w in result["warnings"]))
        finally:
            os.unlink(name)

    @patch("nano_coding.core.scanner.get_staged_files")
    def test_run_audit_scan_fallback_to_staged(self, mock_staged):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# TODO\n")
            name = f.name
        mock_staged.return_value = [name]
        try:
            result = run_audit_scan(files=None)
            self.assertTrue(any("TODO comment found" in w for w in result["warnings"]))
        finally:
            os.unlink(name)

    def test_run_audit_scan_exclude(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write("console.log('test');\n")
            name = f.name
        try:
            result = run_audit_scan(files=[name], exclude=[name])
            self.assertEqual(result["warnings"], [])
        finally:
            os.unlink(name)


if __name__ == "__main__":
    unittest.main()
