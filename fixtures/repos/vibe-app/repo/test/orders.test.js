import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { after, before, test } from 'node:test';

// each test file works on its own data file, never on data/db.json
const dataFile = path.join(os.tmpdir(), `comptoir-orders-${process.pid}.json`);
process.env.DATA_FILE = dataFile;
process.env.LOG_LEVEL = 'silent';
const { app } = await import('../src/app.js');

const server = http.createServer(app);
let base = '';

before(async () => {
  await new Promise((resolve) => server.listen(0, resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(() => {
  server.close();
  fs.rmSync(dataFile, { force: true });
});

const customer = { name: 'Ana Morel', phone: '0611223344' };

test('an order is created pending, with its total in cents', async () => {
  const res = await fetch(`${base}/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      customer,
      items: [
        { productId: 'croissant', quantity: 3 },
        { productId: 'baguette-tradition', quantity: '2' },
      ],
      pickupDate: '2026-05-16',
    }),
  });
  assert.equal(res.status, 201);
  const order = await res.json();
  assert.equal(order.status, 'pending');
  assert.equal(order.totalCents, 3 * 120 + 2 * 130);
  assert.equal(order.total, '6,20 €');
  assert.deepEqual(order.items[1], { productId: 'baguette-tradition', quantity: 2 });

  const read = await fetch(`${base}/orders/${order.id}`);
  assert.equal(read.status, 200);
  assert.equal((await read.json()).number, order.number);
});

test('an unknown product is refused', async () => {
  const res = await fetch(`${base}/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer, items: [{ productId: 'eclair-cafe', quantity: 1 }] }),
  });
  assert.equal(res.status, 400);
});

test('an order above the stock is refused and nothing is saved', async () => {
  const res = await fetch(`${base}/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer, items: [{ productId: 'tarte-pommes', quantity: 7 }] }),
  });
  assert.equal(res.status, 409);
  const orders = await (await fetch(`${base}/orders`)).json();
  assert.equal(orders.filter((o) => o.items[0].productId === 'tarte-pommes').length, 0);
});

test('an order without a phone number is refused', async () => {
  const res = await fetch(`${base}/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer: { name: 'Ana Morel' }, items: [{ productId: 'croissant', quantity: 1 }] }),
  });
  assert.equal(res.status, 400);
});

test('an unknown order answers 404', async () => {
  const res = await fetch(`${base}/orders/ord_nope`);
  assert.equal(res.status, 404);
});
