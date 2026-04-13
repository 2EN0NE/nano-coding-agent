# AI Coding Guardian

AI辅助编码项目的常驻原则守护者。通过轻量级CLI工具和Git钩子来强制执行`AGENTS.md`规范。

## 安装

```bash
pip install .
```

## 命令

### `nano-coding guard install <project>`
将pre-commit钩子和基础`principles/`目录安装到Git仓库中。

```bash
nano-coding guard install .
```

### `nano-coding guard validate <project>`
验证项目是否满足基础治理规则：
- `AGENTS.md`存在且包含`## 基础原则`
- 没有禁止的根目录
- 源文件不超过1000行
- 测试已存在

### `nano-coding guard merge --principles <file> --target <AGENTS.md>`
将源markdown文件中的原则块合并到现有的`AGENTS.md`中，通过语义相似度去重。

```bash
nano-coding guard merge --principles principles/core.md --target AGENTS.md
```

### `nano-coding guard scan --path <project>`
对项目运行安全和审计扫描。报告阻塞性问题、警告和建议。

```bash
nano-coding guard scan --path .
```

### `nano-coding principle-review <project>`
审查目标项目的核心指导原则合规性。默认启用全部检查。

- `--check-changes`：检查核心原则文档（AGENTS.md、README.md 等）是否有未提交的变更，并要求人工确认。
- `--separate-concerns`：检查 AGENTS.md 中是否正确使用 `NANO_CODING_GENERATED` 标记块与分隔符。
- `--length-limit`：扫描原则文档和原则块，对超过 1000 行的文件或超过 150 行的原则块发出告警。

```bash
nano-coding principle-review .
nano-coding principle-review . --check-changes
```

> `principles/core.md` 中不再包含手动标签；运行 `nano-coding guard merge` 时，系统会根据 `skills/` 目录中各命令的实现与 CI/CD hooks 的集成情况，自动为原则标题和实践条目生成 `[suggest]`、`[support]` 或 `[control]` 等标签。

## CLI架构

### 技能自动发现

`nano-coding` 通过扫描 `skills/` 目录自动注册命令。每个 skill 文件只需暴露一个 `click.Group` 变量 `cli`，无需修改主入口文件即可自动挂载到根 CLI。

### Help自动生成机制

所有命令及参数的展示均通过 Click 框架的装饰器自动生成：

- **命令发现**：`pkgutil.iter_modules()` 运行时扫描 `nano_coding/skills/`
- **参数列表**：`@click.option()` 和 `@click.argument()` 装饰器自动提取 `--选项名`
- **帮助文本**：函数 docstring 自动生成命令描述和 Examples

因此，新增技能只需创建 `nano_coding/skills/<name>.py`，定义命令及其 `@click.option()`，运行 `nano-coding --help` 即可自动看到新命令及其所有可用参数。

### 原则标签映射（与 Help 无关）

`@register_practice` 装饰器仅用于 `guard merge` 时计算原则标签（`[support]` / `[control]`），不参与 `--help` 生成。

## 理念

- **极简**：零重型依赖；运行时仅使用Python标准库和PyYAML
- **Agent优先**：工具以`AGENTS.md`为唯一事实来源
- **自我治理**：本仓库由`nano-coding guard validate`进行自我验证

## 许可证

MIT
