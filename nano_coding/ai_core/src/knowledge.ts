import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

export type KnowledgeCategory = "session" | "decision" | "pattern";

export interface KnowledgeEntry {
  title: string;
  category: KnowledgeCategory;
  content: string;
  timestamp: string;
}

const CATEGORY_DIRS: Record<KnowledgeCategory, string> = {
  session: "sessions",
  decision: "decisions",
  pattern: "patterns",
};

export function ensureKnowledgeRoot(projectRoot: string): string {
  const root = join(projectRoot, ".nano-coding-agent", "knowledge");
  if (!existsSync(root)) {
    mkdirSync(root, { recursive: true });
  }
  for (const dir of Object.values(CATEGORY_DIRS)) {
    const path = join(root, dir);
    if (!existsSync(path)) {
      mkdirSync(path, { recursive: true });
    }
  }
  return root;
}

export function writeKnowledge(projectRoot: string, entry: KnowledgeEntry): string {
  const root = ensureKnowledgeRoot(projectRoot);
  const dir = join(root, CATEGORY_DIRS[entry.category]);
  const slug = entry.title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  const filename = `${entry.timestamp.slice(0, 10)}-${slug}.md`;
  const filepath = join(dir, filename);

  const lines = [
    "---",
    `title: ${entry.title}`,
    `category: ${entry.category}`,
    `timestamp: ${entry.timestamp}`,
    "---",
    "",
    entry.content,
  ];

  writeFileSync(filepath, lines.join("\n"), "utf-8");
  return filepath;
}

export function readKnowledgeCategory(projectRoot: string, category: KnowledgeCategory): string {
  const root = ensureKnowledgeRoot(projectRoot);
  const dir = join(root, CATEGORY_DIRS[category]);
  if (!existsSync(dir)) {
    return "";
  }

  const files = readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .sort()
    .reverse();

  const parts: string[] = [];
  for (const file of files) {
    parts.push(`## ${file}\n\n${readFileSync(join(dir, file), "utf-8")}`);
  }
  return parts.join("\n\n");
}
