import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

// Same hard limits as ~/lonca/AGENTS.md, the Claude deny rules and the PATH shims every lane gets.
// shortcut: regex on the command text, not a shell parser; the pre-push hook backs up the git rules.
const BLOCKED: Array<[RegExp, string]> = [
  [/\bgit\s+push\b[^\n;&|]*\s(--force(-with-lease)?|-f)\b/, "no force-push"],
  [/\bgit\s+push\b[^\n;&|]*\s(\S+:)?(main|master)\b/, "never push main/master; push your branch and open a PR"],
  [/\bgit\s+push\b[^\n;&|]*--no-verify/, "don't skip the pre-push hook"],
  [/\bgh\s+pr\s+merge\b|\bgh\s+api\b[^\n]*merge/, "only the owner merges"],
  [/\bgit\s+reset\s+--hard\b/, "no reset --hard"],
  [/\bgit\s+clean\b/, "no git clean"],
  [/\bgit\s+branch\s+-D\b/, "no branch deletion"],
  [/\b(pkill|killall)\b/, "stop only processes you started, by PID"],
  [/ALLOW_MAIN_PUSH/, "owner-only override"],
  [/\bgit\s+config\b[^\n]*(core\.hooksPath\s+\S|--unset[^\n]*core\.hooksPath)/, "don't change git hooks"],
];

export function blockedReason(command: string): string | null {
  for (const [re, why] of BLOCKED) if (re.test(command)) return `lonca guard: blocked (${why}). Stop and report to the owner.`;
  return null;
}

export default function guard(pi: ExtensionAPI) {
  pi.on("tool_call", async (event) => {
    // bash commands, and eval (py/js) code that can shell out (subprocess, os.system, child_process)
    const input = event.input as { command?: unknown; code?: unknown };
    let text: string;
    if (event.toolName === "bash") text = String(input.command ?? "");
    else if (event.toolName === "eval") text = String(input.code ?? "");
    else return;
    const reason = blockedReason(text);
    if (reason) return { block: true, reason };
  });
}
