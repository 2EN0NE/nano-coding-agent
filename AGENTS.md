# AICoding开发规范

本文档定义AI coding AGENTS的开发规范，包含AI Agent协作的共性原则和最佳实践。

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

## CLI 技能注册机制（实现细节）

### 命令注册流程

1. **模块扫描**：`cli.py` 使用 `pkgutil.iter_modules(nano_coding.skills.__path__)` 遍历 `skills/` 目录
2. **动态导入**：对每个模块执行 `importlib.import_module(f"nano_coding.skills.{name}")`
3. **约定挂载**：检查模块是否有 `cli` 属性且为 `click.Group` 类型，通过 `cli.add_command(group, name=name.replace("_", "-"))` 挂载到根 CLI

### Help 递归展示

根 CLI 使用自定义 `RecursiveHelpGroup(click.Group)` 重写 `format_commands()`：

- **Group 处理**：输出 group 名称和 `short_help`，然后缩进递归输出其子命令
- **子命令处理**：输出命令名、short_help，以及从 `cmd.get_params(ctx)` 提取的 `[--选项名]` 列表
- **Leaf Group 特殊处理**：对于无子命令的 group（如 `principle-review`），直接显示 group 名称和其 options

### 参数元数据来源

| 展示内容 | 来源 | 是否自动 |
|---------|------|----------|
| 命令路径 | `skills/` 目录结构 | ✅ 扫描发现 |
| 选项列表 | `@click.option()` / `@click.argument()` | ✅ 装饰器提取 |
| 帮助文本 | 函数 docstring | ✅ docstring |
| 原则标签 | `@register_practice` | ❌ 仅用于 merge |

因此，添加新 skill 的完整流程：
1. 创建 `nano_coding/skills/<skill_name>.py`
2. 定义 `cli = click.Group()`
3. 用 `@cli.command()` + `@click.option()` 定义子命令
4. 运行 `nano-coding --help` 自动可见
