Task: find owner decisions and rules that are NOT yet in the shared memory, and draft them as candidates for the owner to approve. Do not write to ~/ai-memory.

Input: the owner-messages file given to you (messages the owner wrote to AI agents, in their language; each headed by timestamp | project folder | session id). Many are task chatter, not durable rules.
Existing memory: ~/ai-memory/MEMORY.md, every project group's ~/ai-memory/*/INDEX.md and the notes they point to (grep by topic before deciding something is missing); ~/lonca/AGENTS.md; any decisions file a project's memory names.

Keep a message only if it states a durable preference, rule or decision that should change how agents act later ("never X", "from now on Y", "I want Z this way"). Skip one-off instructions, questions, anything already captured with the same meaning, and things the owner only discussed without deciding. If a later message reverses an earlier one, keep the latest and say so. Never copy secrets, passwords, tokens or customer personal data.

Output: write candidates.md next to the input file, at most 30 candidates, most important first:
### N. <short English title>
- group: owner | setup | <project group> | personal
- rule: <one English sentence an agent can follow>
- owner said: "<short quote in the owner's words>" (<date>, <project>, session <id>)
- why it matters: <one line>
- confidence: high | medium
End with: "Checked N messages; K already in memory; M one-off; candidates: X". Return a 10-line summary.
