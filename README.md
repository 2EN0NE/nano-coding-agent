# AI Coding Guardian

AI辅助编码项目的常驻原则守护者。通过轻量级CLI工具和Git钩子来强制执行`AGENTS.md`规范。

## 安装

推荐使用 [uv](https://docs.astral.sh/uv/) 管理虚拟环境和依赖：

```bash
# 1. 创建虚拟环境
uv venv

# 2. 以可编辑模式安装
uv pip install -e .
```

## 初始化项目

### `uv run nano-coding install <project>`

在目标Git仓库中创建 `.nano-coding-agent/` 目录，作为该项目的本地Agent上下文空间。安装过程会执行以下操作：

- 创建 `.nano-coding-agent/` 目录结构
- 写入 `config.json`、`AGENTS.md` 和 `version` 文件
- 创建 `skills/`、`hooks/`、`principles/` 子目录
- 将内置原则复制到 `principles/core.md`
- 将pre-commit钩子复制到 `hooks/pre-commit`
- 为所有内置命令生成 `SKILL.md` 并放入 `skills/{name}/SKILL.md`
- 在 `.git/hooks/` 中安装全局调度脚本

```bash
uv run nano-coding install .
```

### `.nano-coding-agent` 目录结构

初始化后，项目中的 `.nano-coding-agent/` 目录结构如下：

```
.nano-coding-agent/
├── config.json          # 项目级配置（JSON）
├── AGENTS.md            # 项目级Agent上下文文档
├── version              # 初始化时的CLI版本号
├── skills/              # 本地技能目录
│   └── {skill-name}/
│       ├── SKILL.md     # 技能的YAML frontmatter + Markdown说明
│       ├── __init__.py  # 可选，Python技能入口
│       ├── main.py      # 可选，Python技能入口
│       └── cli.py       # 可选，Python技能入口
├── hooks/               # Git钩子脚本
│   └── pre-commit
└── principles/          # 原则块文件
    └── core.md
```

## 命令

所有命令均通过 `uv run` 运行，无需手动激活虚拟环境：

### `uv run nano-coding validate <project>`
验证项目是否满足基础治理规则：
- `AGENTS.md`存在且包含`## 基础原则`
- 没有禁止的根目录
- 源文件不超过1000行
- 测试已存在

### `uv run nano-coding update [target]`
将`principles/`目录下的所有原则块合并到`AGENTS.md`中，通过语义相似度去重。
- 默认目标为当前目录的`AGENTS.md`
- 可传入目录路径，自动查找该目录下的`AGENTS.md`
- 若目标文件或`principles/`目录不存在，输出 ERROR

```bash
uv run nano-coding update
uv run nano-coding update .
uv run nano-coding update /path/to/project
```

### `uv run nano-coding scan --path <project>`
对项目运行安全和审计扫描。报告阻塞性问题、警告和建议。

```bash
uv run nano-coding scan --path .
```

### `uv run nano-coding principle-review <project>`
审查目标项目的核心指导原则合规性。默认启用全部检查。

- `--check-changes`：检查核心原则文档（AGENTS.md、README.md 等）是否有未提交的变更，并要求人工确认。
- `--separate-concerns`：检查 AGENTS.md 中是否正确使用 `NANO_CODING_GENERATED` 标记块与分隔符。
- `--length-limit`：扫描原则文档和原则块，对超过 1000 行的文件或超过 150 行的原则块发出告警。

```bash
uv run nano-coding principle-review .
uv run nano-coding principle-review . --check-changes
```

> `principles/core.md` 中不再包含手动标签；运行 `nano-coding update` 时，系统会根据 `skills/` 目录中各命令的实现与 CI/CD hooks 的集成情况，自动为原则标题和实践条目生成 `[suggest]`、`[support]` 或 `[control]` 等标签。

## 本地 skill 优先机制

`nano-coding` 支持在项目级 `.nano-coding-agent/skills/` 目录中定义本地 skill。本地 skill 的加载遵循以下规则：

- **发现路径**：`.nano-coding-agent/skills/{skill-name}/SKILL.md`
- **祖先遍历**：CLI 会从当前工作目录向上遍历到 Git 根目录，收集路径上所有 `.nano-coding-agent` 目录，优先使用最近的配置
- **覆盖内置命令**：本地 skill 与内置 skill 同名时，本地 skill 优先挂载到 CLI
- **类型支持**：
  - `type: markdown`：纯文本 skill，执行时直接输出 Markdown body
  - `type: python`：通过 `entrypoint` 字段（格式 `module.path:function_name`）动态加载 Python 命令对象

## SKILL.md 格式

每个本地 skill 必须包含一个 `SKILL.md` 文件，格式为 YAML frontmatter + Markdown body：

```markdown
---
name: my-skill
description: 我的自定义技能
type: python
entrypoint: main:cli
principles:
  核心原则:
    - 测试先行
---

## 说明

这是一个自定义技能的示例文档。

## Parameters

- `--path`: 目标项目路径
```

格式要求：
- 必须以 `---` 开头和结束的 YAML frontmatter
- `name`：skill 标识名（决定 CLI 命令名）
- `description`：short help 文本
- `type`：`markdown` 或 `python`
- `entrypoint`（可选）：当 `type` 为 `python` 时，指向 skill 目录内 Python 模块中的 `click.Command` 对象
- `body`：frontmatter 分隔符之后的所有 Markdown 内容

## CLI架构

### 技能自动发现

`nano-coding` 的 CLI 注册分为两个层级：

1. **内置 skill**：在 `nano_coding/skills/` 目录下以 Python 模块形式实现，启动时通过 `_BUILTIN_SKILLS` 字典直接注册
2. **本地 skill**：运行时扫描当前项目（及祖先目录）的 `.nano-coding-agent/skills/`，读取 `SKILL.md` 并动态挂载

本地 skill 支持以下挂载方式：
- 如果 `SKILL.md` 声明了 `entrypoint` 且 skill 目录中存在对应的 Python 模块文件，则动态导入该 `click.Command`
- 如果没有 Python 实现，则生成一个默认的 markdown 输出命令

### Help自动生成机制

所有命令及参数的展示均通过 Click 框架的装饰器自动生成：

- **命令发现**：运行时扫描 `nano_coding/skills/` 和 `.nano-coding-agent/skills/`
- **参数列表**：`@click.option()` 和 `@click.argument()` 装饰器自动提取 `--选项名`
- **帮助文本**：函数 docstring 自动生成命令描述和 Examples

因此，新增内置 skill 只需创建 `nano_coding/skills/<name>.py`，定义命令及其 `@click.option()`，运行 `nano-coding --help` 即可自动看到新命令及其所有可用参数。

### 原则标签映射（与 Help 无关）

`@register_practice` 装饰器仅用于 `update` 时计算原则标签（`[support]` / `[control]`），不参与 `--help` 生成。

## 理念

- **极简**：零重型依赖；运行时仅使用Python标准库和PyYAML
- **Agent优先**：工具以`AGENTS.md`为唯一事实来源
- **自我治理**：本仓库由`nano-coding validate`进行自我验证

## 许可证

MIT
