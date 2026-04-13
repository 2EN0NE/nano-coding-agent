import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from nano_coding.core.principles import PrincipleBlock, resolve_principle_tags
from nano_coding.skills.guard import cli as guard_cli


class TestPrincipleTags(unittest.TestCase):
    def test_principle_level_control_when_all_hooks(self):
        registry = {
            "测试原则": {
                "实践A": {"command_paths": ["cmd"], "in_hooks": True},
                "实践B": {"command_paths": ["cmd2"], "in_hooks": True},
            }
        }
        incoming = [
            PrincipleBlock(
                title="测试原则",
                body="- 实践A：描述A\n- 实践B：描述B",
            )
        ]
        with patch(
            "nano_coding.core.registry.collect_principle_status", return_value=registry
        ):
            result = resolve_principle_tags(incoming, "/fake")

        self.assertEqual(result[0].title, "[control] 测试原则")

    def test_principle_level_control_some(self):
        registry = {
            "测试原则": {
                "实践A": {"command_paths": ["cmd"], "in_hooks": True},
                "实践B": {"command_paths": ["cmd2"], "in_hooks": True},
                "实践C": {"command_paths": ["cmd3"], "in_hooks": False},
            }
        }
        incoming = [
            PrincipleBlock(
                title="测试原则",
                body="- 实践A：描述A\n- 实践B：描述B\n- 实践C：描述C",
            )
        ]
        with patch(
            "nano_coding.core.registry.collect_principle_status", return_value=registry
        ):
            result = resolve_principle_tags(incoming, "/fake")

        self.assertEqual(result[0].title, "[control some] 测试原则")

    def test_principle_level_support_some(self):
        registry = {
            "测试原则": {
                "实践A": {"command_paths": ["cmd"], "in_hooks": False},
                "实践B": {"command_paths": ["cmd2"], "in_hooks": False},
                "实践C": {"command_paths": [], "in_hooks": False},
            }
        }
        incoming = [
            PrincipleBlock(
                title="测试原则",
                body="- 实践A：描述A\n- 实践B：描述B\n- 实践C：描述C",
            )
        ]
        with patch(
            "nano_coding.core.registry.collect_principle_status", return_value=registry
        ):
            result = resolve_principle_tags(incoming, "/fake")

        self.assertEqual(result[0].title, "[support some] 测试原则")

    def test_principle_level_support(self):
        registry = {
            "测试原则": {
                "实践A": {"command_paths": ["cmd"], "in_hooks": False},
                "实践B": {"command_paths": ["cmd2"], "in_hooks": False},
            }
        }
        incoming = [
            PrincipleBlock(
                title="测试原则",
                body="- 实践A：描述A\n- 实践B：描述B",
            )
        ]
        with patch(
            "nano_coding.core.registry.collect_principle_status", return_value=registry
        ):
            result = resolve_principle_tags(incoming, "/fake")

        self.assertEqual(result[0].title, "[support] 测试原则")

    def test_principle_level_suggest(self):
        registry = {
            "测试原则": {
                "实践A": {"command_paths": [], "in_hooks": False},
                "实践B": {"command_paths": [], "in_hooks": False},
            }
        }
        incoming = [
            PrincipleBlock(
                title="测试原则",
                body="- 实践A：描述A\n- 实践B：描述B",
            )
        ]
        with patch(
            "nano_coding.core.registry.collect_principle_status", return_value=registry
        ):
            result = resolve_principle_tags(incoming, "/fake")

        self.assertEqual(result[0].title, "[suggest] 测试原则")

    def test_practice_level_tags_in_body(self):
        registry = {
            "测试原则": {
                "实践A": {"command_paths": ["cmd"], "in_hooks": True},
                "实践B": {"command_paths": ["cmd2"], "in_hooks": False},
                "实践C": {"command_paths": [], "in_hooks": False},
            }
        }
        incoming = [
            PrincipleBlock(
                title="测试原则",
                body="- 实践A：描述A\n- 实践B：描述B\n- 实践C：描述C",
            )
        ]
        with patch(
            "nano_coding.core.registry.collect_principle_status", return_value=registry
        ):
            result = resolve_principle_tags(incoming, "/fake")

        body = result[0].body
        self.assertIn("[control] - 实践A：描述A", body)
        self.assertIn("[support] - 实践B：描述B", body)
        self.assertIn("[suggest] - 实践C：描述C", body)

    def test_merge_command_outputs_tags(self):
        runner = CliRunner()
        principles_path = str(
            Path(__file__).resolve().parents[2] / "principles" / "core.md"
        )

        with runner.isolated_filesystem():
            agents_path = "AGENTS.md"
            Path(agents_path).write_text("# Project\n\n## 基础原则\nSome rules.\n")

            with patch(
                "nano_coding.core.registry.collect_principle_status"
            ) as mock_status:
                mock_status.return_value = {
                    "最重要原则：核心指导原则需要由人类审核": {
                        "变更确认": {
                            "command_paths": ["cmd"],
                            "in_hooks": False,
                        },
                    },
                    '行为边界与"防呆"原则 (Guardrails & Boundaries)': {},
                }
                result = runner.invoke(
                    guard_cli,
                    [
                        "merge",
                        "--principles",
                        principles_path,
                        "--target",
                        agents_path,
                    ],
                )

            self.assertEqual(result.exit_code, 0)
            output = Path(agents_path).read_text()
            self.assertIn("[support] 最重要原则：核心指导原则需要由人类审核", output)
            self.assertIn(
                '[suggest] 行为边界与"防呆"原则 (Guardrails & Boundaries)', output
            )


if __name__ == "__main__":
    unittest.main()
