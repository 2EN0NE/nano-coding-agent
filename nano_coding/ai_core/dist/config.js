import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import YAML from "yaml";
export function loadConfig(projectRoot) {
    const configPath = join(projectRoot, ".nano-coding-agent", "agent.yaml");
    if (!existsSync(configPath)) {
        throw new Error(`Agent config not found: ${configPath}`);
    }
    const content = readFileSync(configPath, "utf-8");
    const parsed = YAML.parse(content);
    if (!parsed.model || !parsed.model.provider || !parsed.model.id) {
        throw new Error("Agent config missing required 'model.provider' and 'model.id'");
    }
    if (!parsed.api_key_source) {
        throw new Error("Agent config missing 'api_key_source'");
    }
    return parsed;
}
export function resolveApiKey(source) {
    if (source.startsWith("env:")) {
        return process.env[source.slice(4)] || undefined;
    }
    if (source === "env") {
        return (process.env.KIMI_API_KEY ||
            process.env.ANTHROPIC_API_KEY ||
            process.env.OPENAI_API_KEY ||
            undefined);
    }
    return source;
}
