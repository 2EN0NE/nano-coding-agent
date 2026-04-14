# AICoding开发规范

本文档定义AI coding AGENTS的开发规范，包含AI Agent协作的共性原则和最佳实践。

## 基础原则

- 核心指导原则需要由人类审核
- 明确行为边界与防呆机制
- 测试先行（TDD First）
- 示例重于描述
- 结构化任务流
- 渐进式披露

## Agent协作范式（推荐实践）

以下Docker沙箱环境和任务生命周期是AICoding的推荐实践，新项目可选择性采用。

### Docker沙箱环境

AI Agent应在Docker隔离环境中运行，确保环境一致性和安全性：

```bash
# 1. 复制环境配置
cp .env.docker.example .env.docker
# 编辑填入 API Key

# 2. 构建并启动
docker-compose up -d --build

# 3. 进入容器
docker exec -it <container-name> bash

# 4. 运行OpenCode
opencode
```

### 任务生命周期

如采用任务领取模式，参考以下流程：

1. 领取任务：原子操作，从任务队列获取任务
2. 创建工作区

> **强烈建议使用 git worktree 创建独立工作区**，原因：
> - **隔离性**：避免多任务同时修改同一代码库导致的冲突
> - **并行性**：可同时在多个worktree中并行处理不同任务
> - **安全性**：任务失败不影响主分支
> - **可清理性**：任务完成后可一键删除，不留残留

```bash
# 创建独立工作区
git worktree add -b task/xxx ../worktrees/task-xxx
cd ../worktrees/task-xxx

# 或者使用 OpenCode 的 worktree_create 命令
opencode --create-worktree -b task-xxx
```

3. 实现功能：在隔离环境中工作
4. 提交代码：git commit 在任务分支
5. Merge与测试

6. 自动合并到 main
7. 标记完成
8. 清理

```bash
# 任务完成后清理
git worktree remove ../worktrees/task-xxx
git branch -D task/xxx
```

9. 经验沉淀：在 PROGRESS.md 记录经验教训

### Git Hook 安装

> **必须安装**：Git钩子需要手动安装到 `.git/hooks/` 目录

```bash
# 安装pre-commit钩子
cp .husky/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit
```

安装后，每次 `git commit` 会自动运行：
1. **Guardian扫描** - Semgrep安全扫描
2. **Audit Agent审计** - LLM逻辑审查
3. **阻塞问题** - 阻止commit，需修复

---

## 多环境分支策略

采用四分支环境模型，确保代码质量逐级验证：

| 分支 | 用途 | 合并方向 |
|------|------|----------|
| DEV | 新特性初步尝试 | → ST |
| ST | 自动化测试/边界条件验证 | → UAT |
| UAT | 人工验收/检核 | → PRD(main) |
| PRD | 正式生产环境 | - |

**流转规则**：
- 所有新功能从 `DEV` 开始
- DEV验证后合并到 `ST` 进行自动化测试
- ST通过后合并到 `UAT` 进行人工验收
- UAT验收通过后合并到 `main(PRD)`
- 禁止跨环境合并（如DEV直接合并到UAT）

**其他工程复用**：此原则可复制到其他工程使用。

---

## 架构设计

### 多级配置查找

配置系统采用三层合并策略，优先级从高到低：

1. **项目级**：当前项目 `.nano-coding-agent/config.json`
2. **用户目录级**：`~/.nano-coding-agent/config.json`
3. **内置默认**：空字典 `{}`

CLI 在解析配置时，会先从当前工作目录向上遍历到 Git 根目录，查找路径上所有 `.nano-coding-agent` 目录。`resolve_config()` 函数会逐层合并配置：低优先级的配置作为基础，高优先级的配置通过递归合并覆盖同名键。对于列表类型的值，合并时会去重拼接。

### 本地优先执行

当 CLI 启动时，会执行以下发现流程：

1. **Ancestor 遍历**：调用 `find_project_agent_dirs()` 从当前目录向上遍历到 Git 根目录，收集所有 `.nano-coding-agent` 目录（从最近到最远排序）
2. **Nearest 选择**：使用 `find_nearest_agent_dir()` 获取距离当前目录最近的 agent 目录作为本次执行的主上下文
3. **本地 skill 加载**：扫描该 agent 目录下的 `skills/` 子目录，读取每个 skill 的 `SKILL.md`，并根据 frontmatter 决定是否加载 Python 实现
4. **覆盖逻辑**：本地 skill 与内置 skill 同名时，本地 skill 优先挂载到根 CLI

### 版本兼容策略

每个通过 `install` 命令初始化的项目都会在 `.nano-coding-agent/version` 中记录当时的 CLI 版本号。运行时，CLI 会执行版本检查：

- 如果本地 `version` 文件中的版本号与当前全局 CLI 版本不一致，会在 stderr 输出 WARNING 告警
- **版本不匹配不会阻止执行**：CLI 继续完成工程级别逻辑（如 validate、scan、principle-review）
- 这种设计允许旧项目在新版本 CLI 下继续工作，同时提醒用户可能需要重新运行 `install` 来同步最新模板和 hooks

---

## CLI 技能注册机制（实现细节）

### 命令注册流程

1. **内置 skill 注册**：`_register_skills()` 先将 `_BUILTIN_SKILLS` 字典中的内置命令和命令组挂载到根 CLI
2. **本地 skill 发现**：通过 `discover_local_skills(agent_dir)` 扫描 `.nano-coding-agent/skills/` 下的子目录
3. **动态导入**：对于声明了 `entrypoint` 且包含 Python 入口文件（`__init__.py` / `main.py` / `cli.py`）的本地 skill，使用 `load_python_skill()` 动态导入 `click.Command`
4. **回退机制**：如果本地 skill 没有 Python 实现，则生成一个默认的 markdown 输出命令
5. **约定挂载**：通过 `cli.add_command(loaded_cmd, name=skill_name)` 将本地 skill 挂载到根 CLI，同名时覆盖内置命令

### Help 递归展示

根 CLI 使用自定义 `RecursiveHelpGroup(click.Group)` 重写 `format_commands()`：

- **Group 处理**：输出 group 名称和 `short_help`，然后缩进递归输出其子命令
- **子命令处理**：输出命令名、short_help，以及从 `cmd.get_params(ctx)` 提取的 `[--选项名]` 列表
- **Leaf Group 特殊处理**：对于无子命令的 group（如 `principle-review`），直接显示 group 名称和其 options

### 参数元数据来源

| 展示内容 | 来源 | 是否自动 |
|---------|------|----------|
| 命令路径 | `skills/` 目录结构 | 扫描发现 |
| 选项列表 | `@click.option()` / `@click.argument()` | 装饰器提取 |
| 帮助文本 | 函数 docstring | docstring |
| 原则标签 | `@register_practice` | 仅用于 merge |

因此，添加新 skill 的完整流程：
1. 创建 `nano_coding/skills/<skill_name>.py`（内置）或 `.nano-coding-agent/skills/<skill_name>/SKILL.md`（本地）
2. 定义 `cli = click.Group()` 或直接实现 `click.Command`
3. 用 `@cli.command()` + `@click.option()` 定义子命令
4. 运行 `nano-coding --help` 自动可见

对于本地 Python skill，可选的入口文件名为 `__init__.py`、`main.py` 或 `cli.py`。`entrypoint` 字段格式为 `module.path:function_name`，其中 `module.path` 是相对于 skill 目录的模块路径。
