# 目录结构设计

本文档描述 Vibe Coding 脚手架的目录设计原则和组织方式。

## 设计原则

1. **可移植性**: 整个 `.vibe-coding-workflow/` 目录可作为模板复制到新项目
2. **关注点分离**: 不同类型的配置和代码放在对应目录
3. **动态生成**: 部分文件通过脚本自动生成（如 AGENTS.md）

## 目录对照表

| 功能类型 | 目录位置 | 说明 |
|---------|---------|------|
| Agent 定义 | `.vibe-coding-workflow/agents/` | AI Agent 的行为规范和约定 |
| Git Hooks | `.vibe-coding-workflow/hooks/` | 提交前的自动化检查 |
| 评估配置 | `.vibe-coding-workflow/evals/` | LLM 输出质量评估 |
| 脚本工具 | `.vibe-coding-workflow/scripts/` | 辅助脚本（如文档生成）|
| 工作流配置 | `.vibe-coding-workflow/workflow.yaml` | 统一的配置入口 |
| 知识库 | `knowledge/` | 项目特有的知识积累 |
| Git Hooks 安装 | `.husky/` | Git 钩子脚本（pre-commit, post-commit）|

## 详细说明

### .vibe-coding-workflow/ (核心工作流)

这是脚手架的核心目录，设计为可移植单元：

```
.vibe-coding-workflow/
├── workflow.yaml          # 统一配置入口
├── agents/               # Agent 规范定义
│   ├── AGENTS.md
│   └── CONVENTIONS.md
├── hooks/                # Hook 框架
│   ├── __init__.py       # BaseHook 接口
│   ├── runner.py         # Hook 调度器
│   ├── hooks.yaml        # Hook 配置
│   ├── requirements.txt
│   └── implementations/  # Hook 实现
│       ├── audit.py      # 审阅 Agent
│       └── guard.py   # 安全扫描
├── evals/                # 评估配置
│   └── deepeval_config.py
└── scripts/              # 辅助脚本
    └── generate_docs.py  # 文档生成
```

### knowledge/ (知识库)

项目特有的经验和知识，供 Agent 参考：

```
knowledge/
├── directory-structure.md  # 本文档
├── README.md             # 知识库索引
└── *.md                  # 其他主题知识
```

添加新知识的规则：
- 文档用 Markdown 格式
- 文件名使用 kebab-case
- 在 README.md 中添加索引

### docs/ (模板文档)

包含模板源文件，供生成器使用：

```
docs/
├── agents-core.md              # Agent 核心规范（模板）
├── agents-scaffold-specific.md # 脚手架特有规范（模板）
└── ...                        # 其他文档模板
```

注意：`agents-scaffold-specific.md` 是脚放架特有的规范，会在生成 AGENTS.md 时被包含。

### scripts/ (项目脚本)

项目级别的辅助脚本（非工作流相关）：

```
scripts/
├── audit_agent.py   # （已迁移到 hooks/）
└── guard.py      # （已迁移到 hooks/）
```

### .husky/ (Git Hooks)

Git 钩子安装目录：

```
.husky/
├── pre-commit     # 提交前检查
└── post-commit    # 提交后生成文档
```

## 添加新功能的目录选择

当需要添加新功能时，按以下规则选择目录：

1. **如果是对 Agent 的规范约束** → `.vibe-coding-workflow/agents/`
2. **如果是自动化检查/验证** → `.vibe-coding-workflow/hooks/implementations/`
3. **如果是 LLM 评估** → `.vibe-coding-workflow/evals/`
4. **如果是辅助脚本** → `.vibe-coding-workflow/scripts/`
5. **如果是项目知识/经验** → `knowledge/`
6. **如果是模板源文件** → `docs/`
7. **如果是 Git 钩子** → `.husky/`

## 配置文件优先级

```
workflow.yaml (统一配置)
    ↓
hooks.yaml (Hook 配置)
    ↓
各模块独立配置
```

## 扩展计划

未来可能添加的目录：

- `.vibe-coding-workflow/skills/` - 自定义技能定义
- `.vibe-coding-workflow/mcp/` - MCP 服务器配置
