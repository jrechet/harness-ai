import { readBody, sendJson } from '../lib/http.js';
import { log } from '../lib/logger.js';
import { verifySignature } from '../lib/payflux.js';
import { readDb, writeDb } from '../store.js';

// POST /webhooks/payflux
export async function handleWebhook(req, res) {
  const raw = await readBody(req);
  if (!verifySignature(raw, req.headers['x-payflux-signature'])) {
    log('warn', 'webhook with a bad signature');
    return sendJson(res, 401, { error: 'invalid signature' });
  }

  let event;
  try {
    event = JSON.parse(raw);
  } catch (err) {
    return sendJson(res, 400, { error: 'invalid JSON' });
  }

  if (event.type === 'payment.succeeded') {
    const db = readDb();
    const order = db.orders.find((o) => o.id === event.data.orderId);
    if (!order) return sendJson(res, 404, { error: 'order not found' });
    if (order.status === 'paid') {
      return sendJson(res, 200, { received: true });
    }
    order.status = 'paid';
    order.paidAt = new Date().toISOString();
    order.paymentId = event.data.paymentId;
    // the stock leaves when the order is paid, not when it is created
    for (const item of order.items) {
      const product = db.products.find((p) => p.id === item.productId);
      if (product) product.stock -= item.quantity;
    }
    writeDb(db);
    log('info', `order ${order.id} paid (${event.id})`);
    return sendJson(res, 200, { received: true });
  }

  // payment.failed, payment.refunded... nothing to do for now
  return sendJson(res, 200, { received: true, ignored: event.type });
}
