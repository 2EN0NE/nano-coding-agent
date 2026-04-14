# BANNED-AGENT-BEHAVIORS.md - Agent禁止的行为
本文档定义AICoding脚手架中Agent不可做的行为。

## 禁止提交包含API Keys明文的文件
正确处理方式:
- 将API Key以环境变量形式在外部提供给容器，配置文件中通过环境变量引用。
