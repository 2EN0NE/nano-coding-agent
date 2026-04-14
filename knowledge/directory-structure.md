# 目录结构设计

本文档描述 nano-coding 项目的目录设计原则和组织方式。

## 设计原则

1. **可移植性**: 整个 `.nano-coding-agent/` 目录可作为模板复制到新项目
2. **关注点分离**: 不同类型的配置和代码放在对应目录
3. **动态生成**: 部分文件通过脚本自动生成（如 AGENTS.md 的合并更新）

## 目录对照表

| 功能类型 | 目录位置 | 说明 |
|---------|---------|------|
| CLI 入口 | `nano_coding/cli.py` | Click 命令注册和本地 skill 发现 |
| 内置命令 | `nano_coding/skills/` | `validate`、`scan`、`install`、`update` 等内置子命令 |
| 核心引擎 | `nano_coding/core/` | `validator.py`、`scanner.py`、`check_engine.py`、`registry.py` 等共享逻辑 |
| 项目配置 | `.nano-coding-agent/` | 项目级 Agent 上下文空间（配置文件、skill、钩子、原则块）|
| 原则块 | `.nano-coding-agent/principles/` 或 `principles/` | 原则源文件，供 `update` 合并到 AGENTS.md |
| 测试代码 | `tests/` | 单元测试（`tests/unit/`）和集成测试（`tests/integration/`）|
| 知识库 | `knowledge/` | 项目特有的知识积累和经验沉淀 |
| Git Hooks 安装 | `.nano-coding-agent/hooks/` 和 `.git/hooks/` | 项目级钩子脚本和全局调度脚本 |

## 详细说明

### nano_coding/ (CLI 包)

这是 `nano-coding` 命令的 Python 包，分为三层：

```
nano_coding/
├── cli.py                 # 根命令和 skill 注册
├── skills/               # 内置子命令实现
│   ├── guard.py          # install / validate / update / scan
│   └── principle_review.py
└── core/                 # 共享核心逻辑
    ├── validator.py      # validate 报告格式化
    ├── scanner.py        # 安全扫描和审计扫描
    ├── check_engine.py   # CheckEngine / Check / Issue 抽象（refactor 后）
    ├── registry.py       # @register_practice 装饰器和原则状态收集
    ├── principles.py     # 原则块提取与合并
    ├── config_loader.py  # 多级配置解析
    ├── installer.py      # nano-coding install 实现
    ├── local_skill_loader.py  # 本地 skill 发现与加载
    └── ...
```

### .nano-coding-agent/ (项目级上下文)

运行 `nano-coding install <project>` 后，目标项目会生成此目录。它是项目与 CLI 交互的本地空间：

```
.nano-coding-agent/
├── config.json          # 项目级配置（JSON）
├── AGENTS.md            # 项目级Agent上下文文档
├── version              # 初始化时的CLI版本号
├── skills/              # 本地技能目录
│   └── {skill-name}/
│       ├── SKILL.md     # 技能的YAML frontmatter + Markdown说明
│       ├── __init__.py  # 可选，Python技能入口
│       ├── main.py      # 可选，Python技能入口
│       └── cli.py       # 可选，Python技能入口
├── hooks/               # Git钩子脚本
│   └── pre-commit
└── principles/          # 原则块文件
    └── core.md
```

### tests/ (测试)

测试按类型严格分离：

```
tests/
├── unit/               # 单元测试（无外部依赖）
└── integration/        # 集成测试（可能调用子进程或临时目录）
```

### knowledge/ (知识库)

项目特有的经验和知识，供 Agent 参考：

```
knowledge/
├── directory-structure.md   # 本文档
├── validate-scan-design.md  # validate/scan 重构设计
├── testing-strategy.md      # 测试策略与反模式
├── security-coding.md       # 安全编码实践
├── README.md                # 知识库索引
└── *.md                     # 其他主题知识
```

添加新知识的规则：
- 文档用 Markdown 格式
- 文件名使用 kebab-case
- 在 `README.md` 中添加索引

### principles/ (原则块源文件)

本仓库（nano-coding 自身）的原则块存放位置。`nano-coding update` 会读取该目录下的 `.md` 文件，合并到 `AGENTS.md`：

```
principles/
└── core.md              # 核心原则块源文件
```

注意：新项目初始化后，原则块默认存放在 `.nano-coding-agent/principles/`；本仓库由于历史原因同时保留根目录 `principles/`，`update` 命令会优先读取 `.nano-coding-agent/principles/`，找不到时回退到根目录 `principles/`。

## 添加新功能的目录选择

当需要添加新功能时，按以下规则选择目录：

1. **如果是新的 CLI 子命令** → `nano_coding/skills/`
2. **如果是 validate/scan 共享的检查逻辑** → `nano_coding/core/check_engine.py`（或 `nano_coding/core/checks/`）
3. **如果是配置解析、skill 加载等共享基础设施** → `nano_coding/core/`
4. **如果是项目级 Agent 规范或原则块** → `.nano-coding-agent/principles/`（新项目）或 `principles/`（本仓库）
5. **如果是项目级自定义 skill** → `.nano-coding-agent/skills/`
6. **如果是项目级 Git 钩子** → `.nano-coding-agent/hooks/`
7. **如果是项目知识/经验** → `knowledge/`
8. **如果是单元/集成测试** → `tests/unit/` / `tests/integration/`

## 配置文件优先级

```
.nano-coding-agent/config.json (项目级配置)
    ↓
~/.nano-coding-agent/config.json (用户目录级配置)
    ↓
内置默认值
```

配置系统采用三层合并策略，高优先级配置递归覆盖低优先级的同名键。

## 扩展计划

未来可能添加的目录：

- `nano_coding/skills/mcp/` - MCP 服务器内置 skill
- `.nano-coding-agent/evals/` - 本地评估配置
