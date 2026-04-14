import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nano_coding import __version__
from nano_coding.core.version_checker import (
    check_version,
    get_global_version,
    get_local_version,
)


class TestGetGlobalVersion(unittest.TestCase):
    def test_returns_package_version(self) -> None:
        self.assertEqual(get_global_version(), __version__)


class TestGetLocalVersion(unittest.TestCase):
    def test_returns_version_when_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent_dir = Path(tmp) / ".nano-coding-agent"
            agent_dir.mkdir()
            (agent_dir / "version").write_text("1.2.3\n")
            self.assertEqual(get_local_version(agent_dir), "1.2.3")

    def test_returns_none_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent_dir = Path(tmp) / ".nano-coding-agent"
            self.assertIsNone(get_local_version(agent_dir))

    def test_returns_none_when_directory_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent_dir = Path(tmp) / ".nano-coding-agent"
            self.assertIsNone(get_local_version(agent_dir))


class TestCheckVersion(unittest.TestCase):
    @patch("nano_coding.core.version_checker.get_global_version", return_value="0.1.0")
    def test_no_output_when_versions_match(self, _mock_global: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent_dir = Path(tmp) / ".nano-coding-agent"
            agent_dir.mkdir()
            (agent_dir / "version").write_text("0.1.0\n")
            with patch("sys.stderr", new=io.StringIO()) as mock_stderr:
                check_version(agent_dir)
                self.assertEqual(mock_stderr.getvalue(), "")

    @patch("nano_coding.core.version_checker.get_global_version", return_value="0.1.0")
    def test_no_output_when_version_file_missing(self, _mock_global: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent_dir = Path(tmp) / ".nano-coding-agent"
            with patch("sys.stderr", new=io.StringIO()) as mock_stderr:
                check_version(agent_dir)
                self.assertEqual(mock_stderr.getvalue(), "")

    @patch("nano_coding.core.version_checker.get_global_version", return_value="0.1.0")
    def test_prints_warning_when_versions_mismatch(self, _mock_global: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent_dir = Path(tmp) / ".nano-coding-agent"
            agent_dir.mkdir()
            (agent_dir / "version").write_text("0.0.1\n")
            with patch("sys.stderr", new=io.StringIO()) as mock_stderr:
                check_version(agent_dir)
                stderr_output = mock_stderr.getvalue()
                self.assertIn("WARNING", stderr_output)
                self.assertIn("0.0.1", stderr_output)
                self.assertIn("0.1.0", stderr_output)
                self.assertIn("\033[33m", stderr_output)
                self.assertIn("\033[0m", stderr_output)

    @patch("nano_coding.core.version_checker.get_global_version", return_value="0.1.0")
    def test_does_not_raise_on_mismatch(self, _mock_global: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent_dir = Path(tmp) / ".nano-coding-agent"
            agent_dir.mkdir()
            (agent_dir / "version").write_text("0.0.9\n")
            try:
                check_version(agent_dir)
            except Exception as e:
                self.fail(f"check_version raised an exception: {e}")
