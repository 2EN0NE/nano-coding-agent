# Beads - AI原生问题追踪

欢迎使用 Beads！本仓库使用 **Beads** 进行问题追踪——这是一款现代化的、AI原生的工具，直接驻留在你的代码库中，与代码并肩工作。

## 什么是 Beads？

Beads 是一种驻留在仓库中的问题追踪方式，非常适合AI coding agents以及希望问题贴近代码的开发者。无需Web UI——一切通过CLI工作，并与git无缝集成。

**了解更多：** [github.com/steveyegge/beads](https://github.com/steveyegge/beads)

## 快速开始

### 常用命令

```bash
# 创建新事务
bd create "Add user authentication"

# 查看所有事务
bd list

# 查看事务详情
bd show <issue-id>

# 更新事务状态
bd update <issue-id> --status in_progress
bd update <issue-id> --status done

# 与git remote同步
bd sync
```

### 事务工作方式

Beads 中的事务具有以下特点：
- **Git原生**：存储在 `.beads/issues.jsonl` 中，像代码一样同步
- **AI友好**：CLI优先设计，完美适配AI coding agents
- **分支感知**：事务可以跟随你的分支工作流
- **始终同步**：与你的提交自动同步

## 为什么选择 Beads？

✨ **AI原生设计**
- 专为AI辅助开发工作流打造
- CLI优先界面与AI coding agents无缝协作
- 无需在Web UI之间切换上下文

🚀 **开发者至上**
- 事务驻留在你的仓库中，就在代码旁边
- 离线工作，推送时同步
- 快速、轻量、不挡道

🔧 **Git集成**
- 与git提交自动同步
- 分支感知的问题追踪
- 智能JSONL合并冲突解决

## 开始使用 Beads

在你自己的项目中体验 Beads：

```bash
# 安装 Beads
curl -sSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash

# 在你的仓库中初始化
bd init

# 创建你的第一个事务
bd create "Try out Beads"
```

## 了解更多

- **文档**：[github.com/steveyegge/beads/docs](https://github.com/steveyegge/beads/tree/main/docs)
- **快速入门指南**：运行 `bd quickstart`
- **示例**：[github.com/steveyegge/beads/examples](https://github.com/steveyegge/beads/tree/main/examples)

---

*Beads：以思考的速度进行问题追踪* ⚡
