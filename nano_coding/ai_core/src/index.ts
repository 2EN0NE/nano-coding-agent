#!/usr/bin/env node
import { runAgent } from "./runtime.js";

async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  if (!command) {
    console.error("Usage: nano-coding-agent-core <command> [options]");
    process.exit(1);
  }

  const projectRoot = process.cwd();

  if (command === "run" || command === "ask") {
    const prompt = args.slice(1).join(" ") || "Review the current project state.";
    const result = await runAgent({ projectRoot, prompt });
    if (result.error) {
      console.error(`[ERROR] ${result.error}`);
      process.exit(1);
    }
    console.log(result.output);
    return;
  }

  if (command === "hook") {
    const nameIndex = args.indexOf("--name");
    const hookName = nameIndex !== -1 ? args[nameIndex + 1] : "unknown";
    let prompt = "";
    if (hookName === "pre-commit") {
      prompt =
        "Review the staged changes for governance violations, security issues, and code quality. Report any blocking issues.";
    } else if (hookName === "post-commit") {
      prompt =
        "Extract the key changes from the latest commit and record any new patterns or decisions to the knowledge base.";
    } else if (hookName === "pre-push") {
      prompt =
        "Review the commits to be pushed for safety and correctness. Report any blocking issues.";
    } else {
      prompt = "Run the appropriate governance check for this hook stage.";
    }
    const result = await runAgent({ projectRoot, prompt });
    if (result.error) {
      console.error(`[ERROR] ${result.error}`);
      process.exit(1);
    }
    console.log(result.output);
    return;
  }

  if (command === "learn") {
    const content = args.slice(1).join(" ");
    if (!content) {
      console.error("Usage: nano-coding-agent-core learn <content>");
      process.exit(1);
    }
    const prompt = `Record the following as project knowledge using the knowledge_learn tool. Infer an appropriate title and category (decision or pattern). Content: ${content}`;
    const result = await runAgent({ projectRoot, prompt });
    if (result.error) {
      console.error(`[ERROR] ${result.error}`);
      process.exit(1);
    }
    console.log(result.output);
    return;
  }

  console.error(`Unknown command: ${command}`);
  process.exit(1);
}

main();
