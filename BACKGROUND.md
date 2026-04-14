# 项目背景与上下文

## 1. 愿景

Guardian 是一个常驻Agent，通过轻量化的本地工具来强制执行AI编码规范。它通过以下方式将`AGENTS.md`从静态文档转变为活跃的契约：
- 提供验证、扫描和原则合并的CLI命令
- 阻拦违反项目规则的Git提交
- 零重型运行时依赖

## 2. 约束

- **最小依赖**：运行时逻辑仅使用Python标准库和PyYAML
- **自托管**：本仓库由`nano-coding guard validate`进行自我验证

## 3. 高层逻辑

### Guardian 工作流
```
git commit → pre-commit hook →
  ├─ nano-coding guard scan  (安全 + 审计扫描)
  └─ nano-coding guard validate (AGENTS.md + 项目规则)
```

### CLI 生命周期
```
nano-coding guard install  → 复制钩子 + 初始化 principles/
nano-coding guard validate → 检查 AGENTS.md、禁止目录、文件长度、测试
nano-coding guard merge    → 去重原则注入到 AGENTS.md
nano-coding guard scan     → Semgrep安全 + 启发式审计扫描
```

## 4. 反模式

- **不要跳过验证**：在认为变更完成之前，先运行`nano-coding guard validate`
- **不要把问题埋在提交信息里**：它们会在审查时浮出水面
- **不要删除失败的测试来通过**：修复代码或测试，而不是信号本身
- **不要硬编码配置**：优先使用环境变量或配置文件
