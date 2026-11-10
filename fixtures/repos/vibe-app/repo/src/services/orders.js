import crypto from 'node:crypto';
import { formatPrice } from '../lib/format.js';
import { toFrenchDate } from '../utils/date.js';

export function newOrderId() {
  return `ord_${crypto.randomBytes(5).toString('hex')}`;
}

// Total in cents. Every item must already be checked against the catalogue.
export function computeTotal(items, products) {
  let total = 0;
  for (const item of items) {
    const product = products.find((p) => p.id === item.productId);
    total += product.priceCents * item.quantity;
  }
  return total;
}

// What the API answers for an order.
export function presentOrder(order) {
  return {
    ...order,
    total: formatPrice(order.totalCents),
    pickupLabel: order.pickupDate ? toFrenchDate(order.pickupDate) : null,
  };
}
