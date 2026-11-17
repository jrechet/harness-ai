import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { after, before, test } from 'node:test';

const dataFile = path.join(os.tmpdir(), `counter-webhook-${process.pid}.json`);
process.env.DATA_FILE = dataFile;
process.env.LOG_LEVEL = 'silent';
const { app } = await import('../src/app.js');

// same value as config/default.json
const WEBHOOK_SECRET = 'whsec_FIXTURE_NOT_A_REAL_SECRET_0000';

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

async function newOrder(quantity) {
  const res = await fetch(`${base}/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      customer: { name: 'Ana Morel', phone: '0611223344' },
      items: [{ productId: 'croissant', quantity }],
    }),
  });
  return res.json();
}

async function stockOf(productId) {
  const products = await (await fetch(`${base}/products`)).json();
  return products.find((p) => p.id === productId).stock;
}

function sendEvent(event, signature) {
  const body = JSON.stringify(event);
  return fetch(`${base}/webhooks/payflux`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Payflux-Signature': signature || crypto.createHmac('sha256', WEBHOOK_SECRET).update(body).digest('hex'),
    },
    body,
  });
}

test('a webhook with a wrong signature is refused', async () => {
  const order = await newOrder(1);
  const res = await sendEvent(
    { id: 'evt_bad', type: 'payment.succeeded', data: { orderId: order.id, paymentId: 'pay_1' } },
    'deadbeef',
  );
  assert.equal(res.status, 401);
  const read = await (await fetch(`${base}/orders/${order.id}`)).json();
  assert.equal(read.status, 'pending');
});

test('payment.succeeded marks the order paid and takes the stock', async () => {
  const before = await stockOf('croissant');
  const order = await newOrder(4);
  assert.equal(await stockOf('croissant'), before);

  const res = await sendEvent({ id: 'evt_1', type: 'payment.succeeded', data: { orderId: order.id, paymentId: 'pay_2' } });
  assert.equal(res.status, 200);

  const read = await (await fetch(`${base}/orders/${order.id}`)).json();
  assert.equal(read.status, 'paid');
  assert.equal(read.paymentId, 'pay_2');
  assert.equal(await stockOf('croissant'), before - 4);
});

test('an event for an unknown order answers 404', async () => {
  const res = await sendEvent({ id: 'evt_2', type: 'payment.succeeded', data: { orderId: 'ord_nope', paymentId: 'pay_3' } });
  assert.equal(res.status, 404);
});
