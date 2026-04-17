"""Integration test fixtures.

Mocks slow external security scanners to keep integration tests fast.
Real scanner logic is covered in unit tests (tests/unit/test_scanner.py).
"""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_security_scan():
    """Auto-mock run_security_scan so semgrep does not slow down integration tests."""
    with patch("nano_coding.skills.guard.run_security_scan") as mock_scan:
        mock_scan.return_value = {
            "blocking": [],
            "warnings": [],
            "suggestions": [],
        }
        yield
