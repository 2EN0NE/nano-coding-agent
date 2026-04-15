import { readFileSync } from "node:fs";
import {
	AuthStorage,
	createAgentSession,
	createFindTool,
	createGrepTool,
	createLsTool,
	createReadTool,
	ModelRegistry,
	SessionManager,
	SettingsManager,
} from "@mariozechner/pi-coding-agent";
import { getModel } from "@mariozechner/pi-ai";

function getArg(name: string): string | undefined {
	const idx = process.argv.indexOf(name);
	if (idx !== -1 && idx + 1 < process.argv.length) {
		return process.argv[idx + 1];
	}
	return undefined;
}

function outputError(error: string): void {
	process.stdout.write(JSON.stringify({ success: false, error }) + "\n");
}

interface RunnerConfig {
	model?: string;
	provider?: string;
	api_key?: string;
	thinking_level?: "off" | "minimal" | "low" | "medium" | "high" | "xhigh";
	cwd?: string;
}

async function main(): Promise<void> {
	const configArg = getArg("--config");
	const promptFile = getArg("--prompt-file");

	if (!configArg || !promptFile) {
		console.error("Usage: node pi_runner.ts --config <json> --prompt-file <path>");
		process.exit(1);
	}

	let config: RunnerConfig;
	try {
		config = JSON.parse(configArg) as RunnerConfig;
	} catch (err) {
		outputError(`Failed to parse --config JSON: ${err instanceof Error ? err.message : String(err)}`);
		process.exit(1);
	}

	const { model: modelId, provider, api_key, thinking_level, cwd } = config;
	if (!modelId || !provider) {
		outputError("Missing required fields in config: model, provider");
		process.exit(1);
	}
	if (!api_key) {
		outputError("Missing required field in config: api_key");
		process.exit(1);
	}

	const workingDir = cwd || process.cwd();

	let promptText: string;
	try {
		promptText = readFileSync(promptFile, "utf-8");
	} catch (err) {
		outputError(`Failed to read prompt file: ${err instanceof Error ? err.message : String(err)}`);
		process.exit(1);
	}

	try {
		const model = getModel(provider as any, modelId as any);
		const authStorage = AuthStorage.inMemory();
		authStorage.setRuntimeApiKey(provider, api_key);
		const modelRegistry = ModelRegistry.inMemory(authStorage);

		const { session } = await createAgentSession({
			cwd: workingDir,
			model,
			thinkingLevel: thinking_level || "medium",
			tools: [
				createReadTool(workingDir),
				createGrepTool(workingDir),
				createFindTool(workingDir),
				createLsTool(workingDir),
			],
			customTools: [],
			sessionManager: SessionManager.inMemory(),
			settingsManager: SettingsManager.inMemory(),
			modelRegistry,
		});

		session.agent.beforeToolCall = async ({ toolCall, args }) => {
			if (toolCall.name === "write" || toolCall.name === "edit") {
				return { block: true, reason: "Audit mode prohibits write/edit operations" };
			}
			if (toolCall.name === "bash") {
				const cmd = (args as any).command?.toLowerCase() || "";
				const dangerous = ["rm", "mv", "chmod", "install", ">", "| sh"];
				if (dangerous.some((p) => cmd.includes(p))) {
					return { block: true, reason: `Audit mode prohibits dangerous bash command: ${cmd}` };
				}
			}
			return undefined;
		};

		let response = "";
		session.subscribe((event) => {
			if (
				event.type === "message_update" &&
				event.assistantMessageEvent.type === "text_delta"
			) {
				response += event.assistantMessageEvent.delta;
			}
		});

		await session.prompt(promptText);
		await session.agent.waitForIdle();

		process.stdout.write(JSON.stringify({ success: true, response }) + "\n");
	} catch (err) {
		outputError(err instanceof Error ? err.message : String(err));
		process.exit(1);
	}
}

main();
