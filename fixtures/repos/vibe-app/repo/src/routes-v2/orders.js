import { readJson, sendJson } from '../lib/http.js';
import { paymentUrl } from '../lib/payflux.js';
import { computeTotal, newOrderId } from '../services/orders.js';
import { formatDateTime, formatMoney } from '../utils/helpers.js';
import { validateOrder } from './validate.js';

function present(order) {
  return {
    ...order,
    total: formatMoney(order.totalCents / 100),
    createdLabel: formatDateTime(order.createdAt),
  };
}

export function ordersHandlers(store) {
  return {
    async create(req, res) {
      const db = store.readDb();
      const checked = validateOrder(await readJson(req), db.products);
      if (!checked.ok) return sendJson(res, checked.status, { errors: checked.errors });

      const order = {
        id: newOrderId(),
        number: db.nextOrderNumber,
        status: 'pending',
        ...checked.value,
        totalCents: computeTotal(checked.value.items, db.products),
        createdAt: new Date().toISOString(),
      };
      order.paymentUrl = paymentUrl(order);
      db.nextOrderNumber += 1;
      db.orders.push(order);
      store.writeDb(db);
      return sendJson(res, 201, { order: present(order) });
    },

    get(req, res, params) {
      const order = store.readDb().orders.find((o) => o.id === params.id);
      if (!order) return sendJson(res, 404, { errors: ['order not found'] });
      return sendJson(res, 200, { order: present(order) });
    },

    list(req, res) {
      const { searchParams } = new URL(req.url, 'http://localhost');
      const status = searchParams.get('status');
      const orders = store.readDb().orders.filter((o) => !status || o.status === status);
      return sendJson(res, 200, { orders: orders.map(present) });
    },

    cancel(req, res, params) {
      const db = store.readDb();
      const order = db.orders.find((o) => o.id === params.id);
      if (!order) return sendJson(res, 404, { errors: ['order not found'] });
      order.status = 'cancelled';
      order.cancelledAt = new Date().toISOString();
      store.writeDb(db);
      return sendJson(res, 200, { order: present(order) });
    },
  };
}
