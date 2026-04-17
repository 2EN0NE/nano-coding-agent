import { createGovernanceTools } from "./guard.js";
import { createKnowledgeTools } from "./knowledge.js";

export function createTools(projectRoot: string) {
  return [...createGovernanceTools(projectRoot), ...createKnowledgeTools(projectRoot)];
}
