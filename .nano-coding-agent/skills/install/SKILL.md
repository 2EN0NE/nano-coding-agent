---
name: install
description: 将pre-commit钩子和基础principles/目录安装到Git仓库中。
type: python
principles:
  行为边界与"防呆"原则 (Guardrails & Boundaries):
  - 禁止操作
---
将pre-commit钩子和基础principles/目录安装到Git仓库中。

    Examples:

        $ uv run nano-coding install .
    

## Parameters
- `<target_dir>`
