// Hidden acceptance test of the cancel-order task: PayFlux delivers the same
// event more than once. The second delivery must change nothing, and be
// answered with a 2xx, or PayFlux keeps sending it.

import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { paid, refunded, startShop } from './server.js';

let shop;
before(async () => {
  shop = await startShop();
});
after(() => shop.stop());

test('replay: payment.succeeded delivered twice takes the stock once', async () => {
  const product = await shop.product();
  const order = await shop.order(product.id, 2);
  const event = paid(order.id);
  for (let delivery = 1; delivery <= 2; delivery += 1) {
    const status = await shop.deliver(event);
    assert.equal(Math.floor(status / 100), 2, `delivery ${delivery} of payment.succeeded answered ${status}`);
  }
  assert.equal(await shop.stockOf(product.id), product.stock - 2);
});

test('replay: payment.refunded delivered three times gives the stock back once', async () => {
  const product = await shop.product();
  const order = await shop.order(product.id, 3);
  await shop.deliver(paid(order.id));

  const event = refunded(order.id);
  for (let delivery = 1; delivery <= 3; delivery += 1) {
    const status = await shop.deliver(event);
    assert.equal(Math.floor(status / 100), 2, `delivery ${delivery} of payment.refunded answered ${status}`);
  }
  assert.equal((await shop.read(order.id)).body.status, 'refunded');
  assert.equal(await shop.stockOf(product.id), product.stock, 'three deliveries of one refund must give the stock back once');
});
