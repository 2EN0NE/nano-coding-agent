import { Agent } from "@mariozechner/pi-agent-core";
import { streamSimple, type Model } from "@mariozechner/pi-ai";
import { loadConfig, resolveApiKey, type AgentConfig } from "./config.js";
import { createTools } from "./tools/index.js";
import { readKnowledgeCategory } from "./knowledge.js";

function buildSystemPrompt(config: AgentConfig, projectRoot: string): string {
  const decisions = readKnowledgeCategory(projectRoot, "decision");
  const patterns = readKnowledgeCategory(projectRoot, "pattern");

  let prompt = `You are the nano-coding-agent, a project-level AI governance assistant running on the pi.dev agent kernel.

Your job is to help maintain code quality and project consistency by:
- Running governance checks (guard_validate, guard_scan)
- Reviewing changes before commits or pushes
- Recording and querying project knowledge
- Answering questions about project rules and history

Current project root: ${projectRoot}
Agent version: ${config.version}
`;

  if (decisions) {
    prompt += `\n\n## Recorded Decisions\n\n${decisions}`;
  }
  if (patterns) {
    prompt += `\n\n## Recorded Patterns\n\n${patterns}`;
  }

  prompt += `\n\nWhen you need to run checks, use the guard_validate and guard_scan tools.
When you learn something important, use the knowledge_learn tool.`;

  return prompt;
}

function createModel(config: AgentConfig): Model<any> {
  return {
    id: config.model.id,
    name: config.model.id,
    api: config.model.provider,
    provider: config.model.provider,
    baseUrl: config.model.baseUrl || "",
    reasoning: config.model.reasoning || false,
    input: [],
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
    contextWindow: config.model.contextWindow || 200000,
    maxTokens: config.model.maxTokens || 8192,
  };
}

export interface RunResult {
  output: string;
  error?: string;
}

export async function runAgent(options: {
  projectRoot: string;
  prompt: string;
}): Promise<RunResult> {
  const config = loadConfig(options.projectRoot);
  const model = createModel(config);
  const apiKey = resolveApiKey(config.api_key_source);

  if (!apiKey) {
    return {
      output: "",
      error: `No API key resolved for source: ${config.api_key_source}. Set the corresponding environment variable.`,
    };
  }

  const agent = new Agent({
    initialState: {
      systemPrompt: buildSystemPrompt(config, options.projectRoot),
      model,
      thinkingLevel: "off",
    },
    streamFn: streamSimple,
  });

  agent.getApiKey = () => apiKey;

  const tools = createTools(options.projectRoot);
  agent.state.tools = tools;

  let output = "";
  agent.subscribe((event) => {
    if (event.type === "message_end" && event.message.role === "assistant") {
      for (const block of event.message.content) {
        if (block.type === "text") {
          output += block.text;
        }
      }
    }
  });

  try {
    await agent.prompt(options.prompt);
    await agent.waitForIdle();
    return { output: output.trim() };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { output: output.trim(), error: message };
  }
}
