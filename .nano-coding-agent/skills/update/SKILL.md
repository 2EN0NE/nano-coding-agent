---
name: update
description: 将principles/目录下的原则块合并到AGENTS.md中，通过语义相似度去重。
type: python
principles:
  最重要原则：核心指导原则需要由人类审核:
  - 共性个性区分
---
将principles/目录下的原则块合并到AGENTS.md中，通过语义相似度去重。

    Examples:

        $ uv run nano-coding update
        $ uv run nano-coding update .
        $ uv run nano-coding update /path/to/project
    

## Parameters
- `<target>`
