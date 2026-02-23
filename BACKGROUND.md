# Project Background & Context

## 1. Vision (为什么存在)

解决 AI Coding 项目缺乏标准化工程规范和安全保障的问题。主要服务于需要构建安全、可维护 AI 辅助开发环境的工程团队。

本脚手架是 **Copier 模板**，用于生成具有以下特性的新项目：
- Docker 隔离的开发环境
- 自动化的安全审计（Guardian + Audit Agent）
- LLM 输出质量评估（DeepEval）
- 跨会话任务记忆（Beads）

## 2. Constraints (约束与底线) - **对 AI 最重要**

- **必须保持零外部依赖**：除 Python/Node 标准库外，核心逻辑不引入额外包
- **安全第一**：禁止提交 API Keys、Secrets，任何凭证泄露必须阻止
- **审计不可绕过**：Guardian 和 Audit Agent 是 commit 的强制检查点
- **原子提交**：每次提交一个逻辑变化，提交后测试必须通过

## 3. High-Level Logic (核心逻辑)

### 项目生成流程
1. Copier 根据用户配置（项目类型、审计级别、评估选项）生成项目
2. 生成的项目的目录结构：
   ```
   .agents/          # Agent 协作规范
   scripts/          # 工具脚本（Guardian、Audit、Beads）
   docs/             # 文档
   evals/            # DeepEval 配置
   .husky/           # Git 钩子
   ```

### 审计工作流
```
git commit → pre-commit hook → 
  ├─ Guardian (Semgrep 静态扫描) → 阻止漏洞/凭证
  └─ Audit Agent (LLM 逻辑审查) → 警告/建议
```

### 任务生命周期
```
领取任务 → 创建 worktree → 实现 → 提交 → 合并 → 清理 → 经验沉淀
```

## 4. Anti-Patterns (避坑指南)

- **不要跳过审计**：即使"只是小改动"也必须运行完整审计流程
- **不要在 commit message 中隐藏问题**：Audit Agent 会检测到
- **不要删除失败的测试来"通过"测试**：这违反了 TDD 原则
- **不要硬编码配置**：使用环境变量或配置文件，保持可移植性
- **不要在生产环境使用沙箱配置**：脚手架的 Docker 配置仅用于开发隔离
