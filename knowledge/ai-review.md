# ai-review 设计与运维说明

## 设计决策

### 为什么选择 Node 子进程桥接

`ai-review` 依赖 `@mariozechner/pi-coding-agent` 提供的 TypeScript 运行时（以下简称 pi）来调度 LLM 对话、工具调用和文本流收集。由于 pi 是一个 Node 生态包，而 nano-coding 本身使用 Python/Click 构建 CLI，因此采用 **Python 主进程 + Node 子进程** 的桥接架构：

- **PiBridge** 负责在 Python 侧准备 prompt、调用参数和临时文件，然后通过子进程调用 pi 运行时。
- prompt 通过 `tempfile.NamedTemporaryFile` 写入磁盘，Node 进程读取后执行 LLM 调用；无论成功或失败，`finally` 块都会清理临时文件。
- `_build_cmd()` 优先使用 `npx --prefix <pi_dir> tsx` 运行 TypeScript 入口；若 `tsx` 不可用，则 fallback 到 `node --experimental-specifier-resolution=node`。
- API Key 仅通过子进程的 `runner_config` 参数传入，不会出现在日志或错误输出中。

这种桥接方式让 Python CLI 能够复用 pi 的会话管理、模型注册表和流式输出能力，而无需将整套 TypeScript 运行时重写为 Python。

## 常见问题

### Node.js 未安装怎么办？

`nano-coding install` 会在初始化项目时尝试检测 Node.js 和 npm：

- 如果系统未安装 Node，install 会输出 `[ERROR] Node.js is required for AI review features...`，但 **不会中断** 安装流程，项目其余功能仍可正常使用。
- 已安装 Node 的项目会在 `.nano-coding-agent/pi/` 目录下生成 `package.json`，并在 `.gitignore` 中自动追加 `.nano-coding-agent/pi/node_modules/`。

修复方式：在运行 `ai-review` 的机器上安装 Node.js（建议 v18+），然后重新执行 `uv run nano-coding install .`。

### API Key 如何配置？

`ai-review` 支持两种配置方式（按优先级从高到低）：

1. **环境变量**
   - `KIMI_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY`

2. **项目级配置文件**
   在 `.nano-coding-agent/config.yaml` 中声明 `ai:` 段：

   ```yaml
   ai:
     provider: kimi-coding
     model: k2p5
     api_key: sk-xxx
   ```

> 注意：不要把真实 API Key 提交到 Git。推荐将 Key 放在环境变量或本地环境专用的 config 中。

### `--model` 参数格式

`--model` 接受 `provider:modelId` 的格式，例如：

```bash
uv run nano-coding ai-review . --model kimi-coding:k2p5
```

如果命令行未传入 `--model`，CLI 会尝试从 `.nano-coding-agent/config.yaml` 的 `ai:` 段读取；若仍不存在，则报错退出。
