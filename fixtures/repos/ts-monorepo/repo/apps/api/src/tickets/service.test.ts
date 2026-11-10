import assert from "node:assert/strict";
import { test } from "node:test";
import { TicketNotFound, TransitionRefused, createTicketService } from "./service.ts";
import { TicketStore } from "./store.ts";

function service() {
  let n = 0;
  return createTicketService({
    store: new TicketStore(),
    now: () => new Date("2026-06-02T08:00:00Z"),
    newId: () => `t${++n}`,
  });
}

test("a new ticket is open", () => {
  const ticket = service().create({ title: "Printer down", requester: "ana@example.test", priority: "normal" });
  assert.equal(ticket.status, "open");
  assert.equal(ticket.id, "t1");
});

test("a refused transition leaves the ticket as it was", () => {
  const tickets = service();
  const { id } = tickets.create({ title: "Printer down", requester: "ana@example.test", priority: "high" });
  assert.throws(() => tickets.changeStatus(id, "resolved"), TransitionRefused);
  assert.equal(tickets.list()[0]?.status, "open");
});

test("the allowed path open, in_progress, waiting, in_progress, resolved, closed", () => {
  const tickets = service();
  const { id } = tickets.create({ title: "Printer down", requester: "ana@example.test", priority: "low" });
  for (const status of ["in_progress", "waiting", "in_progress", "resolved", "closed"] as const) {
    assert.equal(tickets.changeStatus(id, status).status, status);
  }
});

test("an unknown ticket", () => {
  assert.throws(() => service().changeStatus("nope", "closed"), TicketNotFound);
});
