import { sendJson } from '../lib/http.js';
import { formatMoney } from '../utils/helpers.js';

export function productsHandlers(store) {
  return {
    list(req, res) {
      const db = store.readDb();
      const products = db.products.map((p) => ({
        id: p.id,
        name: p.name,
        priceCents: p.priceCents,
        price: formatMoney(p.priceCents / 100),
        stock: p.stock,
        available: p.stock > 0,
      }));
      return sendJson(res, 200, { products });
    },
  };
}
