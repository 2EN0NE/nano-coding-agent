# Validate / Scan 重构设计文档

本文档记录 `nano-coding validate` 与 `nano-coding scan` 的职责边界重构设计，以及共享检查引擎 `CheckEngine` 的架构决策。

## 现状问题

重构前，两个命令的职责和实现存在以下问题：

1. **validate 职责模糊**：`validator.py:validate_project()` 是一个约 225 行的单体函数，混合了文件系统遍历、正则匹配和硬编码原则元数据。新增检查只能往这个函数里堆代码。
2. **scan 输出不统一**：`guard.py:scan()` 直接打印 `[SECURITY BLOCKING]` 等前缀行，没有统一的报告格式化器；`run_audit_scan()` 默认仅扫描 staged files，与“全面扫描”的语义预期冲突。
3. **代码无法复用**：validate 和 scan 各自维护自己的检查逻辑，同样的规则（如文件长度、敏感文件存在性）在两个地方重复实现或遗漏。
4. **Hook 匹配 bug**：`registry.py` 中使用 `" ".join(cp) in hooks_text` 导致 `"validate validate --check-agents-abort"` 无法匹配 hook 文本 `"python3 -m nano_coding.cli validate ."`。

## 目标

- **validate**：定位为快速、纯代码、可在 Git hook 中安全运行的检查命令。不加参数时默认运行所有纯编码检查；退出码仅由 blocking 问题决定。
- **scan**：定位为全面扫描命令，包含编码检查 + LLM/外部工具判断，输出详细报告，支持交互式分页浏览。
- **共享引擎**：提取 `CheckEngine`，让 validate 和 scan 共享同一套检查实现，避免重复代码。

## 设计概述

### 1. CheckEngine 抽象

新建 `nano_coding/core/check_engine.py`，定义三层抽象：

#### Issue（问题）

```python
@dataclass
class Issue:
    path: str | None          # 关联文件路径（可选）
    line: int | None          # 关联行号（可选）
    rule_id: str              # 检查规则标识
    message: str              # 人类可读描述
    principle: str            # 对应原则标题
    practice: str             # 对应实践条目
    severity: Literal["blocking", "warning"]
```

#### Check（检查规则）

每个检查规则实现为一个类：

```python
class Check:
    name: str                 # 命令行 flag 名（如 check-agents-abort）
    principle: str            # 原则名称
    practice: str             # 实践名称
    requires_llm: bool = False
    severity: Literal["blocking", "warning"] = "warning"

    def run(self, project_root: Path) -> list[Issue]:
        ...
```

现有 `validator.py` 中的 10 项检查（如 `agents_md_exists`、`forbidden_dirs`、`file_length`、`test_separation` 等）全部迁移为独立的 `Check` 子类。新增 11 项 `[suggest]` 级检查也按同样模式实现。

#### CheckEngine（引擎）

```python
class CheckEngine:
    def register(self, check: Check) -> None: ...
    def run_all(
        self,
        project_root: Path,
        names: list[str] | None = None,
        include_llm: bool = False,
    ) -> dict[str, list[Issue]]: ...
```

- `register()`：向引擎注册一个检查规则。
- `run_all()`：运行所有已注册检查；若传 `names`，只运行指定检查；若 `include_llm=True`，同时运行 `requires_llm=True` 的检查。
- 返回结果按 `severity` 分组，供上层命令格式化输出。

### 2. validate 命令重构

`guard.py:validate()` 重构后行为：

1. 实例化 `CheckEngine`，注册所有 `requires_llm=False` 的检查。
2. **无 `--check-*` flag 时**：调用 `engine.run_all()`，运行全部纯编码检查。
3. **有特定 `--check-*` flag 时**：调用 `engine.run_all(names=[...])`，仅运行指定检查（保留向后兼容的 4 个旧 flag）。
4. 使用 `validator.py:format_validation_report()` 格式化结果（保持现有报告风格）。
5. `--interactive` 仍通过 `show_report_interactively()` 分页展示。
6. 退出码：`blocking` 非空则 `exit 1`，否则 `exit 0`。

特性总结：

| 属性 | 取值 |
|------|------|
| 速度 | fast |
| 依赖 | 纯 Python，无网络/LLM/外部工具 |
| 适用场景 | Git hook、CI 前置检查 |
| 默认行为 | 运行所有 coding-only 检查 |
| 输出驱动 | exit-code driven |
| 问题分级 | blocking + warning |

### 3. scan 命令重构

`guard.py:scan()` 重构后行为：

1. 实例化 `CheckEngine`，注册所有检查（包含 `requires_llm=False` 和未来的 `requires_llm=True`）。
2. 默认扫描**完整项目树**（遵守 `EXCLUDE_DIRS` 配置）。
3. 仅当显式传入 `--staged` 时，才限制为 staged files（与旧行为相反）。
4. 保留 `run_security_scan()`（semgrep）和 `run_audit_scan()`（regex）的结果，统一转换为 `Issue` 后汇入 `CheckEngine` 报告。
5. 生成统一报告，包含 `SUMMARY`、`BLOCKING`、`WARNINGS`、`SUGGESTIONS` 四个区块。
6. `--interactive` / `-i` 使用 `show_report_interactively()`（或 `click.echo_via_pager()`）实现 less 风格分页。
7. 退出码：`blocking` 非空则 `exit 1`，否则 `exit 0`。

特性总结：

| 属性 | 取值 |
|------|------|
| 速度 | slower（含 semgrep、可能含 LLM）|
| 依赖 | coding + LLM / 外部工具 |
| 适用场景 | 本地开发、发布前全面审计 |
| 默认行为 | 扫描整个项目树 |
| 输出驱动 | report-driven |
| 交互特性 | `--interactive` 分页器 |
| 问题分级 | blocking + warning + suggestion |

### 4. CheckEngine 如何在两者间共享

```
                    ┌─────────────────────────────────────┐
                    │         nano_coding/core/           │
                    │        check_engine.py            │
                    │  ┌─────────┐    ┌─────────────┐   │
                    │  │  Check  │ ←──│ CheckEngine │   │
                    │  │ classes │    │  (shared)   │   │
                    │  └────┬────┘    └──────┬──────┘   │
                    └───────┼────────────────┼──────────┘
                            │                │
           ┌────────────────┘                └────────────────┐
           ▼                                                   ▼
┌─────────────────────┐                            ┌─────────────────────┐
│   validate command  │                            │    scan command     │
│  (guard.py:validate)│                            │   (guard.py:scan)   │
├─────────────────────┤                            ├─────────────────────┤
│ engine = CheckEngine│                            │ engine = CheckEngine│
│ register(coding-    │                            │ register(all checks)│
│   only checks)      │                            │ include_llm=True    │
│ run_all(llm=False)  │                            │ run_all(llm=True)   │
│ format as validate  │                            │ + semgrep results   │
│ report              │                            │ + regex audit       │
│ exit-code driven    │                            │ unified report      │
└─────────────────────┘                            │ --interactive pager │
                                                   └─────────────────────┘
```

关键点：
- **单一定义**：每个检查规则只写一次，在 `Check` 子类中实现。
- **运行时裁剪**：validate 通过 `include_llm=False` 和 `names` 过滤，只运行自己需要的子集。
- **格式解耦**：CheckEngine 只负责收集 `Issue`，报告格式由各自命令决定（validate 保持原有简洁格式，scan 使用新的统一报告）。

## 决策日志

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| CheckEngine 位置 | `nano_coding/core/check_engine.py` | ✅ 采用 | 与 `validator.py`、`scanner.py` 平级，作为共享基础设施 |
| 新增 suggest 检查的 severity | blocking / warning | warning | `[suggest]` 标签语义对应建议级，不应破坏 hook 的阻断语义 |
| scan 默认扫描范围 | staged files / full tree | full tree | 与“全面扫描”的语义一致；旧行为通过 `--staged` 显式保留 |
| validate 默认行为 | 只运行旧检查 / 运行全部 coding 检查 | 运行全部 coding 检查 | 降低用户使用成本，一个命令覆盖所有纯代码 enforce 项 |
| LLM 检查归属 | validate / scan / 两者 | 仅 scan | validate 必须 hook-safe，LLM 调用可能耗时且不稳定 |
| 分页器实现 | `click.echo_via_pager()` / 自定义 tempfile+less | 自定义 `show_report_interactively()` | 已有实现，可控性高，支持 `PAGER` 环境变量回退 |
| 向后兼容 | 保留旧 flag / 重命名 flag | 保留旧 flag | 现有 `--check-agents-abort` 等 4 个 flag 名称和行为完全不变 |
| 插件系统 | 动态发现 / 静态注册 | 静态注册 | 避免过度抽象，保持扁平；新增检查只需在 `guard.py` 中 `engine.register(...)` |

## 迁移影响

- **CLI 用户**：无感知。旧 flag 行为不变，`validate .` 不加 flag 时会多运行一些 warning 级检查，但 exit code 仍只由 blocking 决定。
- **Hook 用户**：pre-commit 中调用 `validate .` 仍然安全、快速、不依赖网络。
- **开发者**：新增检查只需实现一个 `Check` 子类并在 `guard.py` 注册，不再修改 `validator.py` 的庞大函数。

## 相关文件

- `nano_coding/core/check_engine.py` — CheckEngine 抽象（新建）
- `nano_coding/core/validator.py` — 报告格式化器保留，检查逻辑迁移
- `nano_coding/core/scanner.py` — semgrep / regex 扫描结果适配为 Issue
- `nano_coding/skills/guard.py` — validate / scan 命令重构入口
- `nano_coding/core/registry.py` — hook 子串匹配 bug 修复
