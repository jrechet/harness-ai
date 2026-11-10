import assert from "node:assert/strict";
import { test } from "node:test";
import { STATUSES } from "@deskly/shared";
import type { Ticket } from "@deskly/shared";
import { statusLabel } from "./status-label.ts";
import { renderTicketList } from "./ticket-list.ts";

const ticket = (over: Partial<Ticket> = {}): Ticket => ({
  id: "t1",
  title: "Printer down",
  requester: "ana@example.test",
  status: "open",
  priority: "normal",
  createdAt: "2026-06-02T08:00:00.000Z",
  updatedAt: "2026-06-02T08:00:00.000Z",
  ...over,
});

test("every shared status has a label", () => {
  for (const status of STATUSES) assert.equal(typeof statusLabel(status), "string", status);
});

test("a title is escaped, never interpreted", () => {
  const html = renderTicketList([ticket({ title: '<img src=x onerror="alert(1)">' })]);
  assert.ok(!html.includes("<img"), html);
  assert.ok(html.includes("&lt;img"));
});

test("a ticket offers exactly the transitions the shared model allows", () => {
  const html = renderTicketList([ticket({ status: "waiting" })]);
  assert.deepEqual([...html.matchAll(/data-status="(\w+)"/g)].map((m) => m[1]).sort(), ["closed", "in_progress"]);
});

test("an empty list says so", () => {
  assert.match(renderTicketList([]), /Aucun ticket/);
});
