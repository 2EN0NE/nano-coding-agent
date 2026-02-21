# SKILLS.md - 技能定义

本文档定义AICoding脚手架中Agent可用的技能。

## 核心技能

### 1. progress-tracker

**用途**: 自动跟踪和持久化进度到progress.txt，防止上下文腐化

**触发**: 任何多步骤任务

**行为**:
- 会话开始时读取progress.txt
- 每轮迭代后写入当前进度
- 记录完成状态、关键决策、经验教训

---

### 2. git-master

**用途**: Git操作专业化

**触发**: commit、rebase、squash、history查询

**行为**:
- 原子提交
- rebase/squash
- 历史搜索（blame、bisect、log -S）
- 始终使用非交互模式

---

### 3. dev-browser

**用途**: 浏览器自动化

**触发**: 导航网站、填写表单、截图、提取数据

**行为**:
- 持久化页面状态
- 支持复杂交互
- 提取动态内容

---

### 4. playwright

**用途**: Playwright MCP浏览器任务

**触发**: 浏览器相关验证、浏览、信息收集

**行为**:
- 浏览器自动化
- 截图验证
- Web应用测试

---

### 5. frontend-ui-ux

**用途**: 前端UI/UX开发

**触发**: 前端开发、样式、动画

**行为**:
- 设计转代码
- 响应式布局
- 动画实现

---

## 审计技能

### 6. guardian

**用途**: 安全扫描

**触发**: pre-commit阶段

**行为**:
- Semgrep规则扫描
- 安全漏洞检测
- 凭证泄露检测
- 返回JSON格式结果

### 7. audit-reviewer

**用途**: 代码逻辑审查

**触发**: 影子审计

**行为**:
- LLM深度分析
- 逻辑错误检测
- 架构合理性评估

---

## 评估技能

### 8. deepeval-runner

**用途**: LLM输出质量评估

**触发**: 评估任务

**行为**:
- 正确性评估
- 相关性评估
- Hallucination检测
- 生成评估报告

---

## 技能使用规范

### 加载优先级

1. **用户安装技能** - 最高优先级
2. **内置技能** - 按需加载
3. **审计技能** - commit前自动加载

### 技能组合

```python
# 典型任务技能组合
task_skill_map = {
    "frontend": ["frontend-ui-ux", "playwright"],
    "backend": ["deepeval-runner"],
    "security": ["guardian"],
    "code_review": ["audit-reviewer"],
    "git_ops": ["git-master"],
}
```
