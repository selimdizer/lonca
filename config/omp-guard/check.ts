// Self-check: bun ~/lonca/config/omp-guard/check.ts
import { blockedReason } from "./index.ts";
const cases: Array<[string, boolean]> = [
  ["git push --force origin x", true], ["git push origin main", true], ["git push origin HEAD:main", true],
  ["git push -u origin feat/main-menu", false], ["git push origin feat/x", false], ["gh pr create --fill", false],
  ["gh pr merge 3 --squash", true], ["git reset --hard", true], ["git reset --soft HEAD~1", false],
  ["pkill -f node", true], ["ALLOW_MAIN_PUSH=1 git push origin main", true], ["git status", false], ["import subprocess; subprocess.run([\"git\",\"push\",\"origin\",\"main\"])", false], ["git config --global core.hooksPath", false], ["git config --global core.hooksPath /tmp/x", true], ["git config --global --unset core.hooksPath", true],
];
let bad = 0;
for (const [cmd, want] of cases) { const got = blockedReason(cmd) !== null; if (got !== want) { bad++; console.log("FAIL", cmd, "want", want); } }
console.log(bad ? `${bad} failing` : `all ${cases.length} cases pass`); process.exit(bad ? 1 : 0);
