# 安全编码实践

本文档记录项目中的安全编码经验和避免误报的实践。

## 动态导入与白名单

### 问题背景

项目早期使用 `pkgutil.iter_modules()` 动态扫描 `skills/` 目录并自动导入所有模块：

```python
for _, name, _ in pkgutil.iter_modules(nano_coding.skills.__path__):
    module = importlib.import_module(f"nano_coding.skills.{name}")
```

**安全风险**：
- 攻击者可在 `skills/` 目录下注入恶意 `.py` 文件
- `pkgutil` 会将其视为合法模块
- `importlib.import_module()` 会执行任意代码

### 解决方案

采用**显式白名单**机制，只导入预定义的 skill 模块：

```python
# cli.py
from nano_coding.skills.guard import commands as guard_commands
from nano_coding.skills.principle_review import cli as principle_review_cli

_SKILL_WHITELIST = {
    "guard": guard_commands,
    "principle-review": principle_review_cli,
}

for name, cmd in _SKILL_WHITELIST.items():
    if isinstance(cmd, click.Group):
        cli.add_command(cmd, name=name)
```

**优点**：
- 显式声明，代码自解释
- 消除动态导入的安全隐患
- 便于代码审查和依赖分析

### 添加新 Skill 的步骤

1. 在 `nano_coding/skills/` 下创建模块（如 `new_skill.py`）
2. 在 `cli.py` 中导入并加入 `_SKILL_WHITELIST`
3. 在 `registry.py` 的 `_SKILL_MODULES` 中加入对应模块引用
4. 更新测试和文档

---

## 审计规则与误报处理

### 当前规则设计

项目使用 `nano_coding/core/scanner.py` 中的 `SUSPICIOUS_PATTERNS` 进行代码审计：

```python
SUSPICIOUS_PATTERNS = {
    "python": [
        (r"print\s*\(", "Print statement found - consider using logging"),
        (r"TODO\b", "TODO comment found"),
    ],
}
```

### 已知误报场景

#### 1. `TODO.md` 文件名被误报

**现象**：代码中出现 `"TODO.md"` 字符串字面量时，正则会匹配到 `TODO`。

**实际场景**：
```python
# 检查是否存在 TODO.md 文件
if (root / "TODO.md").exists():
    warnings.append("Found TODO.md")
```

**处理建议**：
- 这种误报是代码逻辑的一部分，不需要修复
- 审计时应人工确认是否为真正的 TODO 注释

#### 2. 测试数据中的 `print()` 被误报

**现象**：测试代码中写入虚拟 Python 文件的内容包含 `print()` 调用。

**实际场景**：
```python
# 创建测试用的 Python 文件
(src_dir / "hello.py").write_text('print("hello")\n')
```

**处理建议**：
- 使用 `sys.stdout.write()` 替代，或
- 人工审查时识别这是测试数据而非真实代码

### 减少误报的改进方案

已实现 `_is_inside_string()` 辅助函数：

```python
def _is_inside_string(line: str, pos: int) -> bool:
    """Check if position in line is inside a string literal."""
    in_single = False
    in_double = False
    escaped = False
    for i, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"' and not in_single:
            in_double = not in_double
        elif char == "'" and not in_double:
            in_single = not in_single
    return in_single or in_double
```

在 `analyze_file()` 中过滤掉字符串字面量内的匹配：

```python
for pattern, message in patterns:
    for match in re.finditer(pattern, content):
        if _is_inside_string(line_content, match_pos):
            continue
        warnings.append(...)
```

### 未来改进方向

1. **使用 AST 而非正则**：Python 标准库 `ast` 模块可精确区分代码结构
2. **规则分级**：区分 `security`（安全）、`style`（风格）、`convention`（约定）
3. **配置文件化**：允许项目自定义规则，而非硬编码

---

## 提交前检查清单

- [ ] 代码不包含真实的 TODO/FIXME 注释（字符串字面量中的除外）
- [ ] 不使用 `print()` 进行日志输出（测试数据除外）
- [ ] 动态导入使用白名单机制
- [ ] 敏感信息不硬编码（使用环境变量或配置文件）
