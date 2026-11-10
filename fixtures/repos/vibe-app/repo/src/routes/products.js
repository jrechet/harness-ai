import { sendJson } from '../lib/http.js';
import { readDb } from '../store.js';
import { formatMoney } from '../utils/helpers.js';

export function listProducts(req, res) {
  const db = readDb();
  const products = db.products.map((p) => ({
    id: p.id,
    name: p.name,
    priceCents: p.priceCents,
    price: formatMoney(p.priceCents / 100),
    stock: p.stock,
  }));
  return sendJson(res, 200, products);
}
