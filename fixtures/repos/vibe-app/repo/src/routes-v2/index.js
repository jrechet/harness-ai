import { sendJson } from '../lib/http.js';
import * as fileStore from '../store.js';
import { ordersHandlers } from './orders.js';
import { productsHandlers } from './products.js';
import { Router } from './router.js';

/**
 * Builds the v2 router. The store is injected so the handlers can be tested
 * without touching the data file.
 */
export function createRouter(store = fileStore) {
  const products = productsHandlers(store);
  const orders = ordersHandlers(store);

  const router = new Router();
  router.get('/health', (req, res) => sendJson(res, 200, { ok: true, version: 2 }));
  router.get('/products', products.list);
  router.post('/orders', orders.create);
  router.get('/orders', orders.list);
  router.get('/orders/:id', orders.get);
  router.post('/orders/:id/cancel', orders.cancel);
  // TODO: POST /webhooks/payflux
  return router;
}

export async function routeV2(req, res, store) {
  const handled = await createRouter(store).handle(req, res);
  if (!handled) sendJson(res, 404, { errors: ['not found'] });
}
