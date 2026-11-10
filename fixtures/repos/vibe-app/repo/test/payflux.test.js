import assert from 'node:assert/strict';
import { test } from 'node:test';

// PayFlux cannot be called from the tests: mock client
const payflux = {
  calls: [],
  async createCheckout(order) {
    this.calls.push(order);
    return { id: 'chk_test_1', url: `https://pay.payflux.example/c/${order.id}` };
  },
};

test('createCheckout returns the payment url', async () => {
  const checkout = await payflux.createCheckout({ id: 'ord_1', totalCents: 500 });
  assert.equal(checkout.url, 'https://pay.payflux.example/c/ord_1');
});

test('createCheckout is called once per order', async () => {
  payflux.calls = [];
  await payflux.createCheckout({ id: 'ord_2', totalCents: 1200 });
  assert.equal(payflux.calls.length, 1);
  assert.equal(payflux.calls[0].totalCents, 1200);
});
