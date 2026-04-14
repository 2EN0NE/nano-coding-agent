---
name: validate
description: 验证项目是否满足基础治理规则。
type: python
principles:
  行为边界与"防呆"原则 (Guardrails & Boundaries):
  - 禁止操作
  测试先行原则（TDD First）:
  - 具体的工具链
  - 区分测试类型
  项目背景文档 (BACKGROUND.md):
  - 创建 BACKGROUND.md
---
验证项目是否满足基础治理规则。

    Examples:

        $ uv run nano-coding validate .
        $ uv run nano-coding validate . --check-agents-abort --check-background
        $ uv run nano-coding validate . --interactive
    

## Parameters
- `<target_dir>`
- `--check-agents-abort`: Validate AGENTS_ABORT.md or BANNED-AGENT-BEHAVIORS.md exists and is non-empty.
- `--check-background`: Validate BACKGROUND.md exists in project root.
- `--check-test-separation`: Validate tests/unit/ and tests/integration/ directories exist.
- `--check-test-commands`: Validate README.md or AGENTS.md contains specific test commands.
- `--interactive/-i`: Display results in an interactive pager (less-style).
