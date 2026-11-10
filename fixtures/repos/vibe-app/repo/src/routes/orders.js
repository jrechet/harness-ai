import { readJson, sendJson } from '../lib/http.js';
import { paymentUrl } from '../lib/payflux.js';
import { computeTotal, newOrderId, presentOrder } from '../services/orders.js';
import { readDb, writeDb } from '../store.js';

export async function createOrder(req, res) {
  const body = await readJson(req);
  if (!body) return sendJson(res, 400, { error: 'invalid JSON' });

  const { customer, items, pickupDate } = body;
  if (!customer || !customer.name || !customer.phone) {
    return sendJson(res, 400, { error: 'customer name and phone are required' });
  }
  if (!Array.isArray(items) || items.length === 0) {
    return sendJson(res, 400, { error: 'at least one item is required' });
  }

  const db = readDb();
  const lines = [];
  for (const item of items) {
    const product = db.products.find((p) => p.id === item.productId);
    if (!product) return sendJson(res, 400, { error: `unknown product ${item.productId}` });
    // the web page sends quantities as strings
    const quantity = Number(item.quantity);
    if (!Number.isInteger(quantity) || quantity < 1) {
      return sendJson(res, 400, { error: 'quantity must be a positive integer' });
    }
    if (quantity > product.stock) {
      return sendJson(res, 409, { error: `not enough stock for ${product.name}` });
    }
    lines.push({ productId: product.id, quantity });
  }

  const order = {
    id: newOrderId(),
    number: db.nextOrderNumber,
    status: 'pending',
    customer: { name: String(customer.name), phone: String(customer.phone) },
    items: lines,
    totalCents: computeTotal(lines, db.products),
    pickupDate: pickupDate || null,
    createdAt: new Date().toISOString(),
  };
  order.paymentUrl = paymentUrl(order);
  db.nextOrderNumber += 1;
  db.orders.push(order);
  writeDb(db);
  return sendJson(res, 201, presentOrder(order));
}

export function getOrder(req, res, id) {
  const db = readDb();
  const order = db.orders.find((o) => o.id === id);
  if (!order) return sendJson(res, 404, { error: 'order not found' });
  return sendJson(res, 200, presentOrder(order));
}

// GET /orders?status=paid&pickupDate=2026-05-09
export function listOrders(req, res, url) {
  const db = readDb();
  const status = url.searchParams.get('status');
  const pickupDate = url.searchParams.get('pickupDate');
  let orders = db.orders;
  if (status) orders = orders.filter((o) => o.status === status);
  if (pickupDate) orders = orders.filter((o) => o.pickupDate === pickupDate);
  return sendJson(res, 200, orders.map(presentOrder));
}
