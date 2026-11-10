import assert from "node:assert/strict";
import { test } from "node:test";
import { STATUSES, canTransition, isStatus, nextStatuses, parseNewTicket } from "./index.ts";

test("every status declares its transitions, and only to known statuses", () => {
  for (const status of STATUSES) {
    for (const next of nextStatuses(status)) assert.ok(isStatus(next), `${status} -> ${next}`);
  }
});

test("closed is terminal and nothing skips straight to resolved", () => {
  assert.deepEqual(nextStatuses("closed"), []);
  assert.equal(canTransition("open", "resolved"), false);
  assert.equal(canTransition("in_progress", "resolved"), true);
});

test("a waiting ticket goes back to work or closes", () => {
  assert.deepEqual([...nextStatuses("waiting")].sort(), ["closed", "in_progress"]);
});

test("parseNewTicket collects every error at once", () => {
  const result = parseNewTicket({ title: " ", requester: "nobody", priority: "urgent" });
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.errors.length, 3);
});

test("parseNewTicket trims and defaults the priority", () => {
  const result = parseNewTicket({ title: "  Printer down ", requester: "ana@example.test" });
  assert.deepEqual(result, { ok: true, value: { title: "Printer down", requester: "ana@example.test", priority: "normal" } });
});
