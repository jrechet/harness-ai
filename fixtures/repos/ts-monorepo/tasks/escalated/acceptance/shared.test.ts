import assert from "node:assert/strict";
import { test } from "node:test";
import { canTransition, isStatus, nextStatuses } from "@deskly/shared";

test("acceptance: escalated is a status with exactly the transitions asked for", () => {
  assert.equal(isStatus("escalated"), true);
  assert.equal(canTransition("in_progress", "escalated" as never), true);
  assert.equal(canTransition("open", "escalated" as never), false);
  assert.deepEqual([...nextStatuses("escalated" as never)].sort(), ["in_progress", "resolved"]);
});
