export default function (pi: any) {
  pi.on("tool_call", async (event: any, _ctx: any) => {
    if (event.toolName === "write") {
      return { block: true, reason: "Audit mode prohibits write operations" };
    }

    if (event.toolName === "edit") {
      return { block: true, reason: "Audit mode prohibits edit operations" };
    }

    if (event.toolName === "bash") {
      const command = event.input?.command as string | undefined;
      if (!command) {
        return undefined;
      }

      const lower = command.toLowerCase();
      const dangerous = ["rm", "mv", "chmod", "install", ">", "| sh"];
      const isDangerous = dangerous.some((pattern) => lower.includes(pattern));

      if (isDangerous) {
        return {
          block: true,
          reason: `Audit mode prohibits dangerous bash command: ${command}`,
        };
      }

      return undefined;
    }

    return undefined;
  });
}
