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
