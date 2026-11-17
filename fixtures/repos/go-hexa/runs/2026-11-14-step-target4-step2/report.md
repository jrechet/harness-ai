I wrote the first delegated-task contract, and the targeted check (`L4.contracts`) went green. The shape is in place, but nothing proves yet that agents work better.

- **The step**: write the contract of the task the owner named, "add an endpoint from a use case, from the handler down to the test", in `.claude/skills/add-endpoint/SKILL.md`, then cite it in a new "Delegated tasks" section of AGENTS.md. The owner pointed to `docs/` for the content, which therefore comes from ADRs 0001, 0002 and 0003, the post-mortem of the double debit and the existing code.
- **Before and after**: we stay at level 1 reached, with level 4 targeted. Level 4 goes from 2/5 to 3/5. Line that flipped: `[ ] → [x] At least one task contract exists and is referenced`.
- **What it changes for the agent**: when it is handed a "new endpoint" ticket, it follows a procedure:
  - it lays the layers in order, from the domain to the handler;
  - it looks the idempotency key up inside the transaction by copying `Transfer` and not `OpenAccount`;
  - it adds the route to `routes()` and never touches the list of exemptions;
  - it translates errors into HTTP codes only in `writeDomainError`;
  - it implements a new port in both adapters (memory and PostgreSQL);
  - it stops and asks if the ticket does not fix the shape of the API or if a migration is needed;
  - it knows when the task is done.
- **What is not proven**: `status` only measures that a file exists and that it is cited. No agent PR has followed this contract yet, so no proof of substance exists. It will come from a harness-harvest on real "add-endpoint" PRs: `L4.clean_prs` stays waiting. Several points of the contract are only held by the review:
  - the key lookup inside the transaction;
  - the `Idempotency-Replayed` header;
  - the absence of floats, since the `lint` job does not block.
- **Files**:
  - `.claude/skills/add-endpoint/SKILL.md` (new);
  - `AGENTS.md` (+3 lines, 44 in total, under the limit of 60).

  I committed nothing. My first command, which combined `cd`, `ls` and `cat`, was refused because nothing could be approved in this session; I did the same reads with the file tools.
- **Questions**:
  1. The contract imposes the `Idempotency-Replayed: true` header on every new write endpoint, in line with the rule of AGENTS.md. Yet this rule is verified by nothing, and `POST /transfers` does not apply it yet. Do we keep this requirement for new endpoints? Proposed default: yes.
  2. Do I commit these two files on a branch and open a PR? Proposed default: yes, branch `harness/add-endpoint-contract`.
- **Possible next step**: `L4.cut_the_agent`. It consists in taking, in `.harness/audit.json`, the first step that exists only in a prompt and having a script or a CI job carry it.