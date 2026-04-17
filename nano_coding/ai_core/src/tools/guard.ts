import type { AgentTool, AgentToolResult } from "@mariozechner/pi-agent-core";
import { Type } from "@sinclair/typebox";
import { spawnSync } from "node:child_process";

const validateTool: AgentTool = {
  name: "guard_validate",
  label: "Validate project governance",
  description: "Run nano-coding guard validate on the project",
  parameters: Type.Object({
    path: Type.String({ description: "Project path to validate" }),
  }),
  async execute(_toolCallId, params): Promise<AgentToolResult<{ exitCode: number | null }>> {
    const { path } = params as { path: string };
    const result = spawnSync("python3", ["-m", "nano_coding.cli", "guard", "validate", path], {
      encoding: "utf-8",
    });
    return {
      content: [{ type: "text", text: result.stdout + result.stderr }],
      details: { exitCode: result.status },
    };
  },
};

const scanTool: AgentTool = {
  name: "guard_scan",
  label: "Scan project security",
  description: "Run nano-coding guard scan on the project",
  parameters: Type.Object({
    path: Type.String({ description: "Project path to scan" }),
    level: Type.Optional(Type.String({ default: "standard" })),
  }),
  async execute(_toolCallId, params): Promise<AgentToolResult<{ exitCode: number | null }>> {
    const { path, level } = params as { path: string; level?: string };
    const args = ["-m", "nano_coding.cli", "guard", "scan", "--path", path];
    if (level) {
      args.push("--level", level);
    }
    const result = spawnSync("python3", args, { encoding: "utf-8" });
    return {
      content: [{ type: "text", text: result.stdout + result.stderr }],
      details: { exitCode: result.status },
    };
  },
};

export function createGovernanceTools(): AgentTool[] {
  return [validateTool, scanTool];
}
