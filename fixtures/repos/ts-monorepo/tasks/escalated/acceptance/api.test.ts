import assert from "node:assert/strict";
import { createServer } from "node:http";
import type { AddressInfo } from "node:net";
import { after, before, test } from "node:test";
import { createApp } from "./http.ts";
import { createTicketService } from "./tickets/service.ts";
import { TicketStore } from "./tickets/store.ts";

let n = 0;
const server = createServer(
  createApp(createTicketService({ store: new TicketStore(), now: () => new Date("2026-06-02T08:00:00Z"), newId: () => `a${++n}` })),
);
let base = "";
before(async () => {
  await new Promise<void>((resolve) => server.listen(0, resolve));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});
after(() => server.close());

const json = (method: string, body: unknown) => ({ method, body: JSON.stringify(body), headers: { "content-type": "application/json" } });

test("acceptance: the API escalates a ticket in progress and refuses to close it from there", async () => {
  const created = await fetch(`${base}/tickets`, json("POST", { title: "Printer down", requester: "ana@example.test" }));
  const { id } = (await created.json()) as { id: string };
  assert.equal((await fetch(`${base}/tickets/${id}`, json("PATCH", { status: "escalated" }))).status, 409);
  assert.equal((await fetch(`${base}/tickets/${id}`, json("PATCH", { status: "in_progress" }))).status, 200);
  assert.equal((await fetch(`${base}/tickets/${id}`, json("PATCH", { status: "escalated" }))).status, 200);
  assert.equal((await fetch(`${base}/tickets/${id}`, json("PATCH", { status: "closed" }))).status, 409);
});
