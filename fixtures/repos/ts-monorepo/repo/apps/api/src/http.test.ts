import assert from "node:assert/strict";
import { createServer } from "node:http";
import type { AddressInfo } from "node:net";
import { after, before, test } from "node:test";
import { createApp } from "./http.ts";
import { createTicketService } from "./tickets/service.ts";
import { TicketStore } from "./tickets/store.ts";

let n = 0;
const server = createServer(
  createApp(createTicketService({ store: new TicketStore(), now: () => new Date("2026-06-02T08:00:00Z"), newId: () => `t${++n}` })),
);
let base = "";

before(async () => {
  await new Promise<void>((resolve) => server.listen(0, resolve));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});
after(() => server.close());

const json = (method: string, body: unknown) => ({ method, body: JSON.stringify(body), headers: { "content-type": "application/json" } });

test("create, list, then move a ticket", async () => {
  const created = await fetch(`${base}/tickets`, json("POST", { title: "Printer down", requester: "ana@example.test" }));
  assert.equal(created.status, 201);
  const { id } = (await created.json()) as { id: string };
  const list = (await (await fetch(`${base}/tickets`)).json()) as unknown[];
  assert.equal(list.length, 1);
  const moved = await fetch(`${base}/tickets/${id}`, json("PATCH", { status: "in_progress" }));
  assert.equal(moved.status, 200);
});

test("an invalid ticket answers 422 with every error", async () => {
  const response = await fetch(`${base}/tickets`, json("POST", { title: "", requester: "x" }));
  assert.equal(response.status, 422);
  assert.equal(((await response.json()) as { errors: string[] }).errors.length, 2);
});

test("a refused transition answers 409 and an unknown status 422", async () => {
  const created = await fetch(`${base}/tickets`, json("POST", { title: "Screen", requester: "bo@example.test" }));
  const { id } = (await created.json()) as { id: string };
  assert.equal((await fetch(`${base}/tickets/${id}`, json("PATCH", { status: "resolved" }))).status, 409);
  assert.equal((await fetch(`${base}/tickets/${id}`, json("PATCH", { status: "archived" }))).status, 422);
});
