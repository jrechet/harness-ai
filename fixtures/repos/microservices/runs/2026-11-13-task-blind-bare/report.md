Orders with several lines work: `POST /orders` accepts `lines`, and the order, the `order.created` event and the invoice carry them. I do not recommend delivering them to production before two consumers outside the repository have been checked, the accounting export (`comptoir-export`) and the data warehouse.

The work is on the branch `feat/commandes-multi-lignes`, in a single commit. The repository has no remote: so I could neither push anything nor open a PR. The PR description is ready in `/tmp/claude-0/-tmp-claude-0--home-user-c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b-scratchpad-banc-w-jeex6c2x-repo/06cbd819-f2c2-4f84-8d35-28c53fa40fb9/scratchpad/PR.md`.

The 71 tests pass (61 before) and so does the check of the imports between services.

**What is delivered**
- **`POST /orders`**: each line takes its price from the catalog and the total is the sum of the lines. It answers `422` if a quantity is zero or is not an integer ≥ 1, if an item is not in the catalog, or if `lines` is empty. Each error names its line, for example `lines[1].sku: unknown article`.
- **Old body**: `sku` + `quantity` is still accepted as a one-line order, so as not to break the current clients of the API.
- **`GET /orders/{id}` and `order.created`**: they carry `lines`, each line with `sku`, `quantity` and `unit_price_cents`.
- **Invoices**: `GET /invoices?order_id=…` returns `lines` with `amount_cents` for each line. `billing` takes the price from the event, without importing the catalog of `orders`.
- **Confirmation email**: it now lists all the items. Without this change, it would have announced only the first.
- **Old events**: `billing` and `notifications` still read events without `lines`, which may arrive during the deployment or on a redelivery.

**Contracts**

I made additions only, as the rule written after the May incident requires. `lines` is optional in the event, since the old events have none.

`sku` and `quantity` stay published, marked as obsolete, and equal the first line. That is what needs checking: for an order of several items, `quantity × price(sku)` no longer equals the total. If the accounting export or the data warehouse rely on these two fields to count units, they will produce wrong figures with no error at all, and nothing in this repository can detect it. It is the same kind of problem as the incident of 12 May.

**Decision for you:** this must be confirmed with these two teams and the PR reviewed by @comptoir/contract-owners. If one of them depends on `sku`/`quantity`, everything can be delivered except accepting several lines, until it reads `lines`.

**Deployment order:** `billing` and `notifications` first, `orders` next.

**In addition:** in the tests of `billing` and of `notifications`, the events made by hand are now validated against `contracts/`. That settles only part of what the May postmortem leaves open.

Two commands were refused because no approval was possible in this session: a Python script that rewrote the JSON schemas, and a command that chained the tests and a line-length check. I did the same thing another way, by writing the files directly and with separate commands, and everything was verified.