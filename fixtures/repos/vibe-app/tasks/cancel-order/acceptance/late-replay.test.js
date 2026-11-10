// Hidden acceptance test of the cancel-order task: PayFlux may deliver again an
// event it already got a 200 for, long after. Here the payment event of an
// order comes back once the order has been refunded.

import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { paid, refunded, startShop } from './server.js';

let shop;
before(async () => {
  shop = await startShop();
});
after(() => shop.stop());

test('late replay: payment.succeeded delivered again after the refund changes nothing', async () => {
  const product = await shop.product();
  const order = await shop.order(product.id, 4);
  const payment = paid(order.id);
  await shop.deliver(payment);
  await shop.deliver(refunded(order.id));
  assert.equal((await shop.read(order.id)).body.status, 'refunded');
  assert.equal(await shop.stockOf(product.id), product.stock);

  const status = await shop.deliver(payment);
  assert.equal(Math.floor(status / 100), 2, `the late delivery answered ${status}`);
  assert.equal((await shop.read(order.id)).body.status, 'refunded', 'a refunded order must not become paid again');
  assert.equal(await shop.stockOf(product.id), product.stock, 'the late delivery must not take the stock again');
});
