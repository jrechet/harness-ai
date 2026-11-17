import assert from 'node:assert/strict';
import { Readable } from 'node:stream';
import { test } from 'node:test';
import { createRouter } from '../src/routes-v2/index.js';

function memoryStore() {
  let db = {
    products: [
      { id: 'croissant', name: 'All-butter croissant', priceCents: 120, stock: 10 },
      { id: 'apple-tart', name: 'Apple tart, 6 slices', priceCents: 1650, stock: 1 },
    ],
    orders: [],
    nextOrderNumber: 1,
  };
  return {
    readDb: () => structuredClone(db),
    writeDb: (next) => {
      db = structuredClone(next);
    },
  };
}

function request(method, url, body) {
  const req = Readable.from(body ? [JSON.stringify(body)] : []);
  req.method = method;
  req.url = url;
  req.headers = {};
  return req;
}

function response() {
  return {
    statusCode: 0,
    body: null,
    writeHead(status) {
      this.statusCode = status;
    },
    end(payload) {
      this.body = payload ? JSON.parse(payload) : null;
    },
  };
}

async function call(router, method, url, body) {
  const res = response();
  const handled = await router.handle(request(method, url, body), res);
  return { handled, status: res.statusCode, body: res.body };
}

const customer = { name: 'Ana Morel', phone: '06 11 22 33 44' };

test('v2 lists the products with their availability', async () => {
  const res = await call(createRouter(memoryStore()), 'GET', '/products');
  assert.equal(res.status, 200);
  assert.equal(res.body.products.length, 2);
  assert.equal(res.body.products[0].available, true);
});

test('v2 creates an order and normalises the phone number', async () => {
  const router = createRouter(memoryStore());
  const res = await call(router, 'POST', '/orders', { customer, items: [{ productId: 'croissant', quantity: 3 }] });
  assert.equal(res.status, 201);
  assert.equal(res.body.order.totalCents, 360);
  assert.equal(res.body.order.customer.phone, '0611223344');
});

test('v2 reports every validation error at once', async () => {
  const router = createRouter(memoryStore());
  const res = await call(router, 'POST', '/orders', { customer: { name: '' }, items: [{ productId: 'nope', quantity: 1 }] });
  assert.equal(res.status, 400);
  assert.equal(res.body.errors.length, 3);
});

test('v2 refuses an order above the stock', async () => {
  const router = createRouter(memoryStore());
  const res = await call(router, 'POST', '/orders', { customer, items: [{ productId: 'apple-tart', quantity: 2 }] });
  assert.equal(res.status, 409);
});

test('v2 cancels an order', async () => {
  const router = createRouter(memoryStore());
  const created = await call(router, 'POST', '/orders', { customer, items: [{ productId: 'croissant', quantity: 1 }] });
  const res = await call(router, 'POST', `/orders/${created.body.order.id}/cancel`);
  assert.equal(res.status, 200);
  assert.equal(res.body.order.status, 'cancelled');
});

test('v2 answers false for an unknown route', async () => {
  const res = await call(createRouter(memoryStore()), 'GET', '/nope');
  assert.equal(res.handled, false);
});
