// Hidden acceptance test of the cancel-order task: what the statement asks,
// over HTTP, on the server started by `node src/server.js`.

import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { paid, refunded, startShop } from './server.js';

let shop;
before(async () => {
  shop = await startShop();
});
after(() => shop.stop());

test('acceptance: a pending order is cancelled and reads back cancelled', async () => {
  const product = await shop.product();
  const order = await shop.order(product.id, 2);

  const res = await shop.cancel(order.id);
  assert.equal(res.status, 200, `POST /orders/{id}/cancel answered ${res.status}`);
  assert.equal(res.body.status, 'cancelled');
  assert.equal(res.body.id, order.id);

  const read = await shop.read(order.id);
  assert.equal(read.body.status, 'cancelled');
  assert.equal(await shop.stockOf(product.id), product.stock, 'cancelling an unpaid order must not move the stock');
});

test('acceptance: cancelling an unknown order answers 404', async () => {
  const res = await shop.cancel('ord_does_not_exist');
  assert.equal(res.status, 404);
});

test('acceptance: a paid order is refused with 409 and stays paid', async () => {
  const product = await shop.product();
  const order = await shop.order(product.id, 2);
  assert.equal(await shop.deliver(paid(order.id)), 200);

  const res = await shop.cancel(order.id);
  assert.equal(res.status, 409);
  assert.equal((await shop.read(order.id)).body.status, 'paid');
});

test('acceptance: payment.refunded puts the order in refunded and gives the stock back', async () => {
  const product = await shop.product();
  const order = await shop.order(product.id, 3);
  await shop.deliver(paid(order.id));
  assert.equal(await shop.stockOf(product.id), product.stock - 3);

  const status = await shop.deliver(refunded(order.id));
  assert.equal(Math.floor(status / 100), 2, `payment.refunded answered ${status}`);
  assert.equal((await shop.read(order.id)).body.status, 'refunded');
  assert.equal(await shop.stockOf(product.id), product.stock);
});
