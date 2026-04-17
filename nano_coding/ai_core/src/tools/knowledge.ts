import type { AgentTool, AgentToolResult } from "@mariozechner/pi-agent-core";
import { Type } from "@sinclair/typebox";
import { writeKnowledge, readKnowledgeCategory, type KnowledgeCategory } from "../knowledge.js";

export function createKnowledgeTools(projectRoot: string): AgentTool[] {
  const learnTool: AgentTool = {
    name: "knowledge_learn",
    label: "Record project knowledge",
    description:
      "Write a knowledge entry to the project's .nano-coding-agent/knowledge/ directory. Category must be 'decision' or 'pattern' for long-term knowledge, or 'session' for ephemeral notes.",
    parameters: Type.Object({
      title: Type.String(),
      category: Type.String({ enum: ["session", "decision", "pattern"] }),
      content: Type.String(),
    }),
    async execute(_toolCallId, params): Promise<AgentToolResult<{ filepath: string }>> {
      const timestamp = new Date().toISOString();
      const filepath = writeKnowledge(projectRoot, {
        title: params.title as string,
        category: params.category as KnowledgeCategory,
        content: params.content as string,
        timestamp,
      });
      return {
        content: [{ type: "text", text: `Knowledge recorded to ${filepath}` }],
        details: { filepath },
      };
    },
  };

  const queryTool: AgentTool = {
    name: "knowledge_query",
    label: "Query project knowledge",
    description: "Read all knowledge entries of a given category",
    parameters: Type.Object({
      category: Type.String({ enum: ["session", "decision", "pattern"] }),
    }),
    async execute(_toolCallId, params): Promise<AgentToolResult<{ count: number }>> {
      const content = readKnowledgeCategory(projectRoot, params.category as KnowledgeCategory);
      return {
        content: [{ type: "text", text: content || "No knowledge entries found." }],
        details: { count: content ? 1 : 0 },
      };
    },
  };

  return [learnTool, queryTool];
}
