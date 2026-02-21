# {{project_name}} - 代码风格指南

本文档定义{{project_name}}项目的代码风格规范。

{% if project_type == 'python' %}
## Python规范

### 命名

- 变量/函数: snake_case
- 类: PascalCase
- 常量: UPPER_CASE

### 格式化

- 使用Black格式化
- 使用Ruff检查
- 类型注解必须

### 导入顺序

1. 标准库
2. 第三方库
3. 本地模块

{% elif project_type == 'typescript' %}
## TypeScript规范

### 命名

- 变量/函数: camelCase
- 类/接口: PascalCase
- 组件: PascalCase

### 格式化

- 使用Prettier
- 使用ESLint
- 严格模式

### 导入

- 使用path aliases
- 禁止相对路径穿越目录

{% elif project_type == 'go' %}
## Go规范

### 命名

- 变量/函数: camelCase
- 包: 小写
- 结构体: PascalCase

### 格式化

- 使用gofmt
- 使用golangci-lint

{% elif project_type == 'rust' %}
## Rust规范

### 命名

- 变量/函数: snake_case
- 结构体/枚举: PascalCase
- 宏: snake_case!

### 格式化

- 使用rustfmt
- 使用clippy
{% endif %}

## 通用规则

- 原子提交原则
- 必须写测试
- 文档注释公共API
