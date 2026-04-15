# 原则实践踩坑记录（Principle Gotchas）

> 本文档记录在项目实践中，AI Agent 与人类开发者遇到的**原则声明与实际操作冲突**的案例，以及对应的处理建议。
> 
> **维护提示**：请定期（建议每月）Review 本目录下的文档，将已被代码修复的陈旧条目标记为 `[RESOLVED]` 或归档到 `archive/` 子目录中。

---

## 条目 1：根目录 `scripts/` 被 `validate` 硬编码拦截

**对应原则**：行为边界与"防呆"原则 (Guardrails & Boundaries) — `禁止目录`

**背景**：
`nano_coding/core/validator.py` 第 169 行的 `ForbiddenDirsCheck` 硬编码了：

```python
forbidden = ["templates", "scripts"]
```

该检查会在 `validate` 和 pre-commit hook 中将根目录存在 `scripts/` 判定为 **blocking** 错误，阻止提交。

**冲突场景**：
在实现 `uv-integration-test` 工作流时，按照常见工程惯例，将一键脚本 `test-integration.sh` 放置于项目根目录的 `scripts/` 下。结果提交时被 pre-commit hook 拦截：

```
[1] Forbidden directory at root: scripts/ (violates "生成项目的禁止规则")
```

**当前状态**：
- `validator.py` **尚未变更**，`forbidden = ["templates", "scripts"]` 仍然有效。
- `.gitignore` 已新增 `.sandbox-integration/`、`.venv-integration/`、`.nano-coding-agent/`。

**处理建议**：
1. **如果项目确实需要根目录 `scripts/`**：应同步修改 `nano_coding/core/validator.py` 的 `ForbiddenDirsCheck`，将 `"scripts"` 从 `forbidden` 列表中移除（或改为 warning 级别）。
2. **临时绕过**：在明确知晓风险的前提下，使用 `git commit --no-verify` 跳过本次 hook 拦截。
3. **迁移路径**：将脚本移动到不被拦截的位置，例如 `bin/` 或 `tests/scripts/`。

**人类确认点**：
> 这一规则是否与当前项目的实际工程习惯一致？如果 `scripts/` 是合理且常见的目录，请考虑修改 validator，或更新原则文档明确说明 `scripts/` 的替代位置。

---

## 维护检查清单

- [ ] 每月检查本文档中的条目是否已被代码修复
- [ ] 已修复的条目添加 `[RESOLVED YYYY-MM-DD]` 标记
- [ ] 超过 6 个月未更新的条目应 Review 是否仍具参考价值
- [ ] 新增 gotcha 时，请在顶部按时间倒序追加
