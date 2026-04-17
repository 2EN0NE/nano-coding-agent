import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@mariozechner/pi-agent-core", () => {
  return {
    Agent: vi.fn().mockImplementation(() => ({
      state: { tools: [] },
      prompt: vi.fn().mockResolvedValue(undefined),
      waitForIdle: vi.fn().mockResolvedValue(undefined),
      subscribe: vi.fn((listener) => {
        listener({
          type: "message_end",
          message: {
            role: "assistant",
            content: [{ type: "text", text: "Validation passed." }],
          },
        });
      }),
      getApiKey: vi.fn(),
    })),
  };
});

vi.mock("@mariozechner/pi-ai", () => {
  return {
    streamSimple: vi.fn(),
  };
});

vi.mock("./config.js", () => {
  return {
    loadConfig: vi.fn(() => ({
      version: "0.1.0",
      model: { provider: "test", id: "test-model" },
      api_key_source: "env:TEST_KEY",
    })),
    resolveApiKey: vi.fn(() => "test-key"),
  };
});

vi.mock("./knowledge.js", () => {
  return {
    readKnowledgeCategory: vi.fn(() => ""),
  };
});

import { runAgent } from "./runtime.js";

describe("runAgent", () => {
  beforeEach(() => {
    process.env.TEST_KEY = "test-key";
  });

  it("returns assistant output on success", async () => {
    const result = await runAgent({ projectRoot: "/tmp/fake", prompt: "hello" });
    expect(result.output).toBe("Validation passed.");
    expect(result.error).toBeUndefined();
  });
});
