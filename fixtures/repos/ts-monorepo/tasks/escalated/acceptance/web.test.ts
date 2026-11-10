import assert from "node:assert/strict";
import { test } from "node:test";
import { STATUSES } from "@deskly/shared";
import type { Ticket } from "@deskly/shared";
import { statusLabel } from "./status-label.ts";
import { renderTicketList } from "./ticket-list.ts";

test("acceptance: every status the shared model knows has a label on screen", () => {
  for (const status of STATUSES) {
    const label = statusLabel(status);
    assert.equal(typeof label, "string", status);
    assert.notEqual(label, "", status);
  }
});

test("acceptance: an escalated ticket renders with its label and its two ways out", () => {
  const ticket = {
    id: "t1", title: "Printer down", requester: "ana@example.test", status: "escalated", priority: "normal",
    createdAt: "2026-06-02T08:00:00.000Z", updatedAt: "2026-06-02T08:00:00.000Z",
  } as unknown as Ticket;
  const html = renderTicketList([ticket]);
  assert.ok(html.includes("Escaladé"), html);
  assert.deepEqual([...html.matchAll(/data-status="(\w+)"/g)].map((m) => m[1]).sort(), ["in_progress", "resolved"]);
});
