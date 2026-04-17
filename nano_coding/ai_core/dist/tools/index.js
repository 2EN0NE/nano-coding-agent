import { createGovernanceTools } from "./guard.js";
import { createKnowledgeTools } from "./knowledge.js";
export function createTools(projectRoot) {
    return [...createGovernanceTools(), ...createKnowledgeTools(projectRoot)];
}
