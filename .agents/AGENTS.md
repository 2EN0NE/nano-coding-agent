# {{project_name}} - Agent协作规范

本文档定义{{project_name}}项目的Agent协作范式。

## 核心原则

- TDD先行
- 明确需求再行动
- 任务跟踪
- 经验积累

## Agent体系

### Guardian

硬性静态分析，Semgrep安全扫描。

### Audit Agent

软性逻辑审计，LLM深度分析。

### Evaluator

LLM输出质量评估，DeepEval集成。

## 审计决策

| 级别 | 内容 | 行为 |
|------|------|------|
| Blocking | 安全漏洞、凭证泄露 | 阻止commit |
| Warning | 代码风格、命名 | 允许commit |
| Suggestion | 性能优化 | 可选记录 |

## Git工作流

```bash
# 开发流程
1. 创建分支
2. 实现功能
3. 运行审计
4. 提交commit
5. 合并到主分支
```

## 验收标准

- [ ] 通过Guardian安全扫描
- [ ] 通过Audit Agent审查
- [ ] 测试通过
- [ ] 代码风格一致


## Beads 任务记忆

使用 bd (Beads) 进行跨会话任务追踪，防止"失忆":

### 安装

```bash
# 在项目中安装 beads 技能
bash scripts/install_beads_skills.sh
```

### 使用

```bash
# 读取任务记忆
python scripts/read_task_beads.py --ready           # 列出就绪任务
python scripts/read_task_beads.py --current-branch  # 当前分支相关任务
python scripts/read_task_beads.py --task-id bd-xxx  # 特定任务

# 保存检查点（在结束会话前）
python scripts/write_task_checkpoint.py \
  --summary "已完成认证重构，修复登录流程" \
  --next-steps "连接前端到新API，更新测试"

# 或更新特定任务
python scripts/write_task_checkpoint.py \
  --task-id bd-xxx \
  --summary "..." \
  --next-steps "..."
```

### 工作流

1. **会话开始**: 运行 `read_task_beads.py --current-branch` 恢复上下文
2. **工作中**: 随时可以查看任务详情
3. **会话结束**: 运行 `write_task_checkpoint.py` 保存进度
