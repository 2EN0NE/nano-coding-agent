<!-- NANO_CODING_GENERATED_START -->
<!-- 以下内容通过 nano-coding 自动生成与维护，请勿手动修改此区域 -->

## 基础原则

---

### [control some] 最重要原则：核心指导原则需要由人类审核

原则：对于重要提供AGENT指导的文档文件，必须用主要编程用户的熟悉语言编写，由人工审核。
实践：

[support] - 变更确认：对起原则指导性的文档文件进行配置，明确这些文件有哪些，在AI Coding过程中Agent如有对这些文件变动（包括原则指导文档列表的配置文件），必须在最后总结时候警告+说明变动内容+要求人类自己审核，设置CICD工具对其变更进行git commit的人工确认（列出核心原则文件变更范围，需要人类手动输入“I have personally reviewed the revisions to the core principles document.”）。
[control] - 共性个性区分：在AGENTS.md中区分共性与个性原则，建议在文档中有如“---”分隔符进行两部分的显示区分，以方便人类阅读，构建认知框架，方便审核。
[support] - 控制长度：每保留必不可少的指令，剔除所有"废话"。条描述建议在150行以内，每个文件控制在1000行以内。如有必要，在实战中进行验证、补充与增强，进行分层分类。但注意，这部分补充AGENT只能建议，最后需要人类自己采纳。
[suggest] - 排除陈腐文档：如果AI Coding实际工作中发现现状与说明文档相违背，询问人类是以当前目标为准——修改文档，还是按文档描述进行Coding。注意这里说的是说明性文档，与项目特色有关，不包含AGENTS.md等最根本性的原则说明文件。

---

### [control] 行为边界与"防呆"原则 (Guardrails & Boundaries)

原则： 明确告诉 AI "绝对不要做什么"，比告诉它"要做什么"更有效。
实践：

[control] - 禁止操作：项目需要禁止的操作集中放到AGENTS_ABORT.md文件下。例如"禁止修改 vendor/ 目录"、"禁止在没有询问的情况下添加重型依赖"、"禁止硬编码颜色"。
[control] - 安全防线： 明确规定"禁止提交 API Keys 或 Secrets"。

---

### [control] 测试先行原则（TDD First）

原则： 每次行动，先设计与思考如何测试，并先编写测试，在AGENTS.md或README.md中让智能体知道如何测试自己的产出。
实践：

[control] - 具体的工具链： 提供完整的带参数命令，如 npm test 或 pytest -v，而不是只说"运行测试"。
[suggest] - 环境特异性： 指明具体的包管理器（如 pnpm vs npm），防止生成错误的安装指令。
[control] - 区分测试类型：单元测试、集成测试、安全测试、性能测试分开设计，放在不同的文件夹下，可用不同命令调起他们，调起的命令写到AGENT知识目录下。必须包含单元测试，强烈建议设计集成测试，如果用户在对话中提出安全、性能问题，则开始设计安全与性能测试。

---

### [suggest] 示例重于描述原则 (Show, Don't Tell)

原则： 一个真实的代码片段胜过三段文字描述，抽象原则之后最好给出具体举例。
实践：

[suggest] - 风格参照： 提供符合项目规范的 UI 组件写法或状态管理模式（如"使用 MUI v3 兼容写法"）。
[suggest] - 反模式避坑： 使用表格或列表列出"坏代码 vs 好代码"的对比。

---

### [suggest] 结构化任务流原则 (Workflow Structure)

原则： 强制要求 AI 在执行前先进行思考与规划。
实践：

[suggest] - Plan-then-Execute： 规定 AI 必须先创建/更新一个 plan.md，并在确认后才开始修改代码。
[suggest] - 测试驱动 (TDD)： 明确要求"在编写实现代码前，必须先编写并运行失败的测试用例"。
[suggest] - 变更理由： 要求 AI 在建议修改时，简要说明其推理逻辑。

---

### [suggest] 渐进式披露原则 (Progressive Disclosure)

原则： 不要在根目录的 AGENTS.md 里堆砌所有子模块的细节。
实践：

[suggest] - 目录分权： 在**大型项目**中，使用子目录下的 AGENTS.md 存储特定模块的规则。
[suggest] - 外部引用： 引导 AI 去读取特定的 .INDEX.md 或 .SUMMARY.md 以获取更深层的架构信息。
[suggest] - AGENTS可读：在读取大量代码后所得到的只是，建议知识与经验放到knowledge目录下，方便Agent与人集中查阅。

---

### [control] 项目背景文档 (BACKGROUND.md)

原则： 每个项目应有独立的背景文档，让 AI Agent 在没有人类语境的情况下也能理解项目的存在理由。
实践：

[suggest] - 建议在项目根目录创建 `BACKGROUND.md` 文件。
[suggest] - 内容应包含：项目愿景、核心约束、业务逻辑、避坑指南。

---

### [suggest] TDD先行

原则：每个任务区分设计、测试与实现Agent，设计Agent先进行接口设计，测试Agent再进行测试代码编写，接着交由实现Agents负责按接口实现不同模块，最后认为任务都完成后交由测试Agent验证。

实践：
[suggest] - 测试一定要区分集成测试与单元测试，测试文件夹下通过二级目录区分不同类型。
[suggest] - 集成测试需严格设计、避免绕过，存在外部环境依赖的，如外部接口请求，需通过接口录制等技术确保集成测试不会受外部不确定性影响。

---

### [suggest] 明确需求再行动

原则：当Agent遇到不确定问题时要先提问确认，先从决定性的高层开始，再到细节，先问"做什么"，再问"怎么做"。

---

### [suggest] 经验积累

原则：每次用户对Agents结果的有效反馈，需提炼经验，补充到相应的地方。

[suggest] - 集中收集：工作中总结有效经验，特别是一些细节要点，建议统一放到./knowledge/目录下，按主题归类。重要经验，可达到原则级别的，需要影响后续所有AGENTS动作的，提醒用户是否要同步到AGENTS.md
[suggest] - 分散规整：当./AGENTS.md内容过多，搜集的重要经验内容又限定在某一模块时，建议在对应子模块目录下创建子AGENTS.md进行经验沉淀。

---

### [suggest] 文档语言

原则：项目文档因以主要开发人员最熟悉的语言编写，鼓励进行多语言文档设置。

实践：
[suggest] - 多语言文档关联：建议参考github多文档关联的跳转形式，进行同一文档不同语言版本之间的关联，跳转链接放文档最上方。
[suggest] - 权威文档（AGENTS.md）保持必须单一语言，说明性文档（README.md）建议多语言（至少包含英语）。

---

### [suggest] Git Commit规范

#### 采用Conventional Commits：

实践：

提交规范参考

```
<type>(<scope>): <subject>

# Type: feat/fix/docs/style/refactor/test/chore
# 示例: feat(eval): add hallucination metric
```

#### 原子提交

实践：

[suggest] - 提交粒度：每次提交一个粒度不应过大，应能够对应到用户感知的一个特性或一个逻辑变化。
[suggest] - 提交前准备：提交前需跑单元测试通过，单元测试执行命令应明确的卸载README中，提交commit前需检查当前变动的文件是否是零时性的、敏感性的等不应加入git管控范围，检查后把这类文件加入到.gitignore再提交。

<!-- NANO_CODING_GENERATED_END -->

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
