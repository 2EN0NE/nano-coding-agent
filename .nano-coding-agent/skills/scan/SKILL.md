---
name: scan
description: 对项目运行安全和审计扫描。报告阻塞性问题、警告和建议。
type: python
principles:
  行为边界与"防呆"原则 (Guardrails & Boundaries):
  - 安全防线
---
对项目运行安全和审计扫描。报告阻塞性问题、警告和建议。

    Examples:

        $ uv run nano-coding scan --path .
    

## Parameters
- `--path`: Directory to scan (default: current directory)
- `--level`: Audit level (default: standard)
