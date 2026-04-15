# 测试策略与验证规范

## 单元测试设计原则

### 禁止巧妙绕过
- 单元测试必须直接调用被测函数，禁止用 mock 替代核心逻辑。
- 对于文件系统操作，使用 `tempfile.TemporaryDirectory` 或 `tmp_path` 创建真实的临时目录和文件，禁止全局状态污染。
- 测试 `local_skill_loader` 时，必须写入真实的 `SKILL.md` 和 Python 模块文件，验证 `importlib` 动态加载、`sys.path` 恢复、异常处理等真实行为。

### CLI 单元测试
- 使用 `click.testing.CliRunner` 调用真实命令对象。
- 允许对 `find_nearest_agent_dir` 做 patch，但 skill 目录、Python 入口文件必须真实创建。
- `test_cli.py` 中的向后兼容测试通过 patch 返回 `None` 来模拟旧项目（无 `.nano-coding-agent/`），验证 CLI 不崩溃且内置命令正常注册。

## 集成测试设计原则

### 必须创建真实临时工程
集成测试必须在一个干净的临时目录中：
1. 创建 `.git/` 目录（模拟 Git 仓库）
2. 写入必要的项目文件（`AGENTS.md`、`README.md`、测试目录等）
3. 使用 `subprocess.run([sys.executable, "-m", "nano_coding.cli", ...])` 执行真实的 CLI 进程
4. 设置 `PYTHONPATH` 指向项目根目录，确保调用的是本地源码而非已安装的全局包
5. 断言 stdout/stderr 内容和进程返回码

### 集成测试环境隔离（uv + sandbox）

为避免污染开发环境，集成测试使用 uv 的 `dependency-groups` 进行依赖隔离：

```toml
[dependency-groups]
integration = [
    "pytest>=7.4",
]
```

一键运行脚本：

```bash
bash scripts/test-integration.sh
```

脚本行为：
1. 重建 `.venv-integration/` 隔离虚拟环境
2. 将当前项目复制到 `.sandbox-integration/`
3. 在沙盒内切换到 `main` 分支（提供典型项目模板）
4. 恢复当前分支的 `tests/integration/`、`nano_coding/` 和 `principles/`
5. 在隔离环境中安装包并运行 `pytest tests/integration/ -v`

**新增集成测试只需**：在 `tests/integration/` 下编写 pytest 函数，无需关心环境创建逻辑。

### 已覆盖的真实场景
| 场景 | 验证点 |
|------|--------|
| `install` 创建完整 `.nano-coding-agent/` 结构 | 目录、文件、版本、钩子可执行权限 |
| 本地 skill 注册与执行 | 写入 `SKILL.md` + `main.py`，`--help` 出现该命令，执行输出预期内容 |
| 版本不匹配告警 | 篡改 `version` 文件后运行 CLI，stderr 出现 WARNING 但不中断 |
| 旧项目向后兼容 | 无 `.nano-coding-agent/` 时 `validate` 和 `scan` 正常运行且不抛异常 |
| `update` 合并原则块 | 临时 `AGENTS.md` 与 `principles/core.md` 合并，生成标记块 |

### 禁止的测试反模式
- ❌ 用 mock 替代整个 install / validate / scan 逻辑
- ❌ 在真实工程目录中直接运行 install
- ❌ 断言 `True is True` 或只检查函数是否被调用
- ❌ 依赖全局环境变量或已安装的全局 CLI 包

## 安全相关测试

- `test_local_skill_loader.py` 中专门验证：
  - 非法 entrypoint 格式返回 `None`
  - 缺失文件返回 `None`
  - 动态导入后 `sys.path` 严格恢复
  - 支持嵌套模块和 `__init__.py` 包结构

## 运行命令

```bash
# 全部测试
pytest tests/ -q

# 仅集成测试
pytest tests/integration/ -v

# 仅单元测试
pytest tests/unit/ -v

# 隔离集成测试（一键沙盒）
bash scripts/test-integration.sh
```

---

> 📝 **经验沉淀提醒**：> > 每次在集成测试工作中发现新的环境冲突、原则冲突或最佳实践，请同步更新本文档或 `knowledge/principle-gotchas.md`。> 建议每月 Review 一次 `knowledge/` 目录，归档已失效的内容，保持知识库与实际代码一致。
