import { isEmpty } from '../utils/helpers.js';

/**
 * Validates the body of POST /orders against the catalogue.
 * @returns {{ ok: true, value: object } | { ok: false, status: number, errors: string[] }}
 */
export function validateOrder(body, products) {
  const errors = [];
  if (!body || typeof body !== 'object') {
    return { ok: false, status: 400, errors: ['body must be a JSON object'] };
  }
  const customer = body.customer || {};
  if (isEmpty(customer.name)) errors.push('customer.name is required');
  if (isEmpty(customer.phone)) errors.push('customer.phone is required');
  if (!isEmpty(customer.phone) && !/^0\d{9}$/.test(String(customer.phone).replace(/\s/g, ''))) {
    errors.push('customer.phone must be a French number');
  }
  if (isEmpty(body.items)) errors.push('items must not be empty');

  const items = [];
  let outOfStock = false;
  for (const item of body.items || []) {
    const product = products.find((p) => p.id === item.productId);
    const quantity = Number(item.quantity);
    if (!product) {
      errors.push(`unknown product ${item.productId}`);
    } else if (!Number.isInteger(quantity) || quantity < 1) {
      errors.push(`quantity of ${item.productId} must be a positive integer`);
    } else if (quantity > product.stock) {
      errors.push(`not enough stock for ${product.name}`);
      outOfStock = true;
    } else {
      items.push({ productId: product.id, quantity });
    }
  }

  if (errors.length > 0) {
    return { ok: false, status: outOfStock && errors.length === 1 ? 409 : 400, errors };
  }
  return {
    ok: true,
    value: {
      customer: { name: String(customer.name).trim(), phone: String(customer.phone).replace(/\s/g, '') },
      items,
      pickupDate: body.pickupDate || null,
    },
  };
}
