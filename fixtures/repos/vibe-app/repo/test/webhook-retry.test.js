import assert from 'node:assert/strict';
import { test } from 'node:test';

// Regression test for the double delivery of PayFlux events.

function makeHandler(state) {
  return function handle(event) {
    const order = state.orders.find((o) => o.id === event.data.orderId);
    if (order.status === 'paid') return { received: true };
    order.status = 'paid';
    state.stock -= order.quantity;
    return { received: true };
  };
}

test('an event delivered twice is processed once', () => {
  const state = { stock: 10, orders: [{ id: 'ord_1', status: 'pending', quantity: 2 }] };
  const handle = makeHandler(state);
  const event = { id: 'evt_1', type: 'payment.succeeded', data: { orderId: 'ord_1' } };

  handle(event);
  handle(event);
  handle(event);

  assert.equal(state.orders[0].status, 'paid');
  assert.equal(state.stock, 8);
});
