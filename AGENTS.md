# AICoding开发规范

本文档定义AI coding AGENTS的开发规范。内容由以下部分组成：

# AICoding开发规范

本文档定义AI coding AGENTS的开发规范，包含AI Agent协作的共性原则和最佳实践。

## 核心原则

### 元原则：阿卡姆剃刀原则 (Minimalism & SNR)

原则： 仅保留必不可少的指令，剔除所有“废话”。
实践：

- 控制长度：每条描述建议在150行以内，每个文件控制在1000行以内。如有必要，在实战中进行验证、补充与增强，进行分层分类。
- 动态调整：移除通用的编程常识（如“编写整洁代码”），只保留AI Coding特有的约束。
- 排除陈腐文档：如果AI Coding实际工作中发现现状与说明文档相违背，询问人类是以当前目标为准——修改文档，还是按文档描述进行Coding。注意这里说的是说明性文档，与项目特色有关，不包含AGENTS.md等最根本性的原则说明文件。

### 行为边界与“防呆”原则 (Guardrails & Boundaries)

原则： 明确告诉 AI “绝对不要做什么”，比告诉它“要做什么”更有效。
实践：

- 禁止操作：项目需要禁止的操作集中放到AGENTS_ABORT.md文件下。例如“禁止修改 vendor/ 目录”、“禁止在没有询问的情况下添加重型依赖”、“禁止硬编码颜色”。
- 安全防线： 明确规定“禁止提交 API Keys 或 Secrets”。 

### 测试先行原则（TDD First）

原则： 每次行动，先设计与思考如何测试，并先编写测试，在AGENTS.md或README.md中让智能体知道如何测试自己的产出。
实践：

- 具体的工具链： 提供完整的带参数命令，如 npm test 或 pytest -v，而不是只说“运行测试”。
- 环境特异性： 指明具体的包管理器（如 pnpm vs npm），防止生成错误的安装指令。
- 区分测试类型：单元测试、集成测试、安全测试、性能测试分开设计，放在不同的文件夹下，可用不同命令调起他们，调起的命令写到AGENT知识目录下。必须包含单元测试，强烈建议设计集成测试，如果用户在对话中提出安全、性能问题，则开始设计安全与性能测试。

### 示例重于描述原则 (Show, Don't Tell)

原则： 一个真实的代码片段胜过三段文字描述，抽象原则之后最好给出具体举例。
实践：

- 风格参照： 提供符合项目规范的 UI 组件写法或状态管理模式（如“使用 MUI v3 兼容写法”）。
- 反模式避坑： 使用表格或列表列出“坏代码 vs 好代码”的对比。 

### 结构化任务流原则 (Workflow Structure)

原则： 强制要求 AI 在执行前先进行思考与规划。
实践：

- Plan-then-Execute： 规定 AI 必须先创建/更新一个 plan.md，并在确认后才开始修改代码。
- 测试驱动 (TDD)： 明确要求“在编写实现代码前，必须先编写并运行失败的测试用例”。
- 变更理由： 要求 AI 在建议修改时，简要说明其推理逻辑。

### 渐进式披露原则 (Progressive Disclosure)

原则： 不要在根目录的 AGENTS.md 里堆砌所有子模块的细节。
实践：

- 目录分权： 在**大型项目**中，使用子目录下的 AGENTS.md 存储特定模块的规则。
- 外部引用： 引导 AI 去读取特定的 .INDEX.md 或 .SUMMARY.md 以获取更深层的架构信息。
- AGENTS可读：在读取大量代码后所得到的只是，建议知识与经验放到knowledge目录下，方便Agent与人集中查阅。

## 工作流要求

### TDD先行

- 先设计测试用例再写代码
- 无对应测试时，先设计并确认
- 代码完成后运行测试回归

### 明确需求再行动

- 不确定时要先提问确认
- 先从决定性的高层开始，再到细节
- 先问"做什么"，再问"怎么做"

### 任务跟踪

- 任务前创建TODO.md，分解原子任务
- 每轮迭代后更新PROGRESS.md
- 完成后删除临时文件

#### PROGRESS.md格式

要包含以下板块:

- 当前目标（Active Goal）： 正在处理的核心功能或 Bug。
- 已完成事项（Done）： 自上次记录以来已提交或测试通过的代码更改。
- 剩余待办（Remaining Tasks）： 下一步需要执行的具体步骤。
- 发现与注意事项（Findings & Notes）： 遇到的阻碍、临时决策或需要下个会话注意的 Bug。 

举例如下:

```markdown
# 进度记录 - [日期]

## 当前状态
- 正在重构用户登录逻辑，目前已完成 API 路由修改。

## 已完成
- [x] 创建了 auth-v2 路由文件。
- [x] 完成了密码加密工具函数的单元测试。

## 待办事项
- [ ] 连接前端登录表单到新路由。
- [ ] 更新相关的集成测试。

## 备注
- 注意：由于 API 变更，需要通知前端团队更新 Header 字段。
```

### 经验积累

- 工作中总结有效经验到knowledge/
- 重要经验，可达到原则级别的，需要影响后续所有AGENTS动作的，同步到AGENTS.md

### 文档语言

- 权威文档（AGENTS.md）保持单一语言
- 说明性文档（README.md）可双语

### Git Commit规范

采用Conventional Commits：

```
<type>(<scope>): <subject>

# Type: feat/fix/docs/style/refactor/test/chore
# 示例: feat(eval): add hallucination metric
```

**原子提交原则**：每次提交一个逻辑变化，提交后测试通过。

---

## Agent协作范式（推荐实践）

以下Docker沙箱环境和任务生命周期是AICoding脚手架的推荐实践，新项目可选择性采用。

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
opencode --create-worktree -b task/xxx
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

# 脚手架特有规范

本文档包含 Vibe Coding 脚手架项目特有的规范，其他项目可根据需要参考。

## 目录结构原则

本脚手架采用 **集中式工作流目录** 设计：

```
.vibe-coding-workflow/  # 所有工作流相关配置
├── workflow.yaml       # 统一配置入口
├── agents/            # Agent 规范
├── hooks/             # Hook 框架 + 实现
├── evals/             # 评估配置
└── scripts/           # 辅助脚本
```

详细说明见 [knowledge/directory-structure.md](./knowledge/directory-structure.md)

## 新功能放置规则

添加新功能时，必须放在正确的目录下：

| 功能 | 目录 |
|-----|------|
| Agent 行为规范 | `.vibe-coding-workflow/agents/` |
| 自动化检查(Hook) | `.vibe-coding-workflow/hooks/implementations/` |
| LLM 评估 | `.vibe-coding-workflow/evals/` |
| 辅助脚本 | `.vibe-coding-workflow/scripts/` |
| 项目知识 | `knowledge/` |
| 模板源文件 | `docs/` |

## 动态文档机制

- `AGENTS.md` 由 `AGENTS.md.tmpl` 通过 `post-commit` hook 自动生成
- 每次 `git commit` 后自动运行 `.vibe-coding-workflow/scripts/generate_docs.py`
- 生成的 `AGENTS.md` 必须提交到版本控制

## Hook 框架规范

新增 Hook 必须：

1. 继承 `hooks.BaseHook` 类
2. 使用 `@hooks.hook()` 装饰器注册
3. 在 `hooks.yaml` 中配置启用
4. 在 `workflow.yaml` 的 git 配置中添加执行顺序

示例：

```python
from hooks import BaseHook, HookResult, hook

@hook(enabled=True, timeout=60)
class MyHook(BaseHook):
    name = "my_hook"
    description = "My custom hook"
    
    def run(self, context):
        return HookResult(name=self.name, success=True)
```

## 配置文件说明

- `workflow.yaml` - 统一配置入口（copier 模板变量在此定义）
- `hooks/hooks.yaml` - Hook 独立配置
- `.husky/pre-commit` - Git 提交前检查
- `.husky/post-commit` - 提交后生成文档

## 依赖管理

- 工作流 Python 依赖：`hooks/requirements.txt`
- 项目级依赖：不在此管理，由具体项目决定

