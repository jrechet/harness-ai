# Audit report format

Reproduce these sections in this order, with these titles. A section without content contains the word "None". The final JSON block follows the given schema exactly.

---

# Harness audit — <process name>

**Scope**: <repo / folders audited> · **Date**: <YYYY-MM-DD> · **Items inventoried**: <n>

## 0. Where this leaves you

The output of `harness status --map` after `.harness/audit.json` is written, then one plain sentence: what this audit changes on the map (the level that needed an audit, the urgent items found) and what comes next. No verdict or layer code here without its plain meaning.

## 1. Summary

- **Health score**: <0–100> — <one sentence: is the agent an accelerator or a pillar?>
- **"Cut the agent" test result**: PASSED / FAILED — <n> process step(s) exist only in prompts.
- **Blocking issues (P1)**: <n>
- **The three actions that change things most**:
  1. …
  2. …
  3. …

The score is computed as: 100, minus 25 per P1, minus 8 per P2, minus 2 per P3, floored at 0. A failed "cut the agent" test caps the score at 60. Lines to remove do not count one by one in the score: the verdict of the file carrying them is what counts.

## 2. Map of the harness

Table of all inventoried items:

| # | Item | Path | Declared layer | Actual layer | Called by | Calls |
|---|---|---|---|---|---|---|

Then the nominal process, step by step, with the layer carrying each step:

| Process step | Carried by | Checked by code? | Dry-run? |
|---|---|---|---|

## 3. Leaks: rules and steps told without enforcement

Process steps or mandatory rules that live only in a prompt, a SKILL.md or an AGENTS.md, with no guardrail in code or pipeline. For each: the rule or step, where it is told (path:line), what happens if the agent skips it, where it should live and with which tool (CLI subcommand, eslint rule, ArchUnit test, PR gate…).

Also mention, in one line each, the rules that **do** have their guardrail: that is the healthy part of the harness and it guides what can be shortened in the instruction files.

## 3b. Context cost (if instruction files are in scope)

| File | Lines loaded (with includes) | Share instruction / reference / noise | Loaded when |
|---|---|---|---|

Followed by one sentence on the justification of the rules (why + incidents cited?) and on the presence of a maintenance clause.

## 3c. Lines to remove (if instruction files are in scope)

Result of the relevance review. Harmful lines first, then useless ones, grouped by homogeneous block, then outdated ones, which are questions.

| File:line | Text | Reason | Proof | Question to the owner? |
|---|---|---|---|---|

Then **Questions to the owner**, numbered, one per line, each with why it is asked and the proposed default. Then one sentence on what remains: how many lines before, how many after, which must absolutely be kept.

## 4. Findings by item

One block per item, in the order P1 → P2 → P3 then KEEP at the end:

### [<VERDICT>] [<P1|P2|P3|—>] <item> — <path>
- **Does today**: …
- **Problem**: … (proof: path:line)
- **Must become**: …
- **Check criterion**: …

KEEP items have one line: `### [KEEP] <item> — <path>` followed by one sentence.

## 5. Remediation plan

Ordered by priority then by dependency.

| Order | Priority | Verdict | Item | Action | Depends on | Check | Human approval required |
|---|---|---|---|---|---|---|---|

## 6. What the audit could not check

Missing files, unreadable workflows, tests that could not run, assumptions made. Empty = "None".

## 7. Machine data

```json
{
  "audit": {
    "process": "<name>",
    "scope": "<repo/folders>",
    "date": "<YYYY-MM-DD>",
    "health_score": 0,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 0 }
  },
  "elements": [
    {
      "id": "<slug>",
      "path": "<path>",
      "declared_layer": "L1|L2|L3|L4",
      "actual_layer": "L1|L2|L3|L4|MIXED",
      "called_by": ["<id>"],
      "calls": ["<id>"],
      "verdict": "KEEP|INLINE|PUSH_DOWN|PROMOTE|MERGE|SPLIT|BLOCK|REMOVE",
      "priority": "P1|P2|P3|null",
      "finding": "<one sentence>",
      "evidence": ["<path:line>"],
      "target": "<one sentence>",
      "check": "<one sentence>"
    }
  ],
  "process_leaks": [
    { "rule": "<rule or step>", "told_in": "<path:line>", "if_skipped": "<consequence>", "belongs_in": "L3|L4", "guard_tool": "<target tool>" }
  ],
  "guarded_rules": [
    { "rule": "<rule>", "told_in": "<path:line>", "guarded_by": "<path of the linter/test/gate>" }
  ],
  "removals": [
    { "path": "<file>", "line": 0, "text": "<the quoted line, shortened if long>", "reason": "useless|harmful|outdated", "evidence": "<where it is discoverable, what contradicts it, what dates it>", "ask_owner": false }
  ],
  "owner_questions": ["<question, with the proposed default>"],
  "instruction_files": [
    { "path": "<path>", "loaded_lines": 0, "instruction_pct": 0, "reference_pct": 0, "noise_pct": 0, "justified_rules": true, "maintenance_clause": true }
  ],
  "remediation": [
    {
      "order": 1,
      "priority": "P1",
      "verdict": "PUSH_DOWN",
      "element": "<id>",
      "action": "<one sentence>",
      "depends_on": [],
      "check": "<one sentence>",
      "needs_human_approval": true
    }
  ],
  "unverified": ["<text>"]
}
```

`harness audit check <file>` refuses this block when `audit.date` is not a day, when `elements` is empty, when an element lacks its `path`, its `verdict` or its `priority` (written `null`, not left out, for a KEEP), when `process_leaks` is not a list, or when `cut_the_agent_test.passed` is `true` while `process_leaks` is not empty: the test cannot pass while a mandatory step lives only in a prompt. `harness status` does not count a file the check refuses.
