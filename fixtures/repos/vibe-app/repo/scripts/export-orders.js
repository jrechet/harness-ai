// Exports the orders of a pickup date as CSV.
//   node scripts/export-orders.js 2026-05-09 > orders-2026-05-09.csv
import { readDb } from '../src/store.js';

const date = process.argv[2];
if (!date) {
  console.error('usage: node scripts/export-orders.js <YYYY-MM-DD>');
  process.exit(1);
}

const db = readDb();
const rows = [['number', 'customer', 'phone', 'items', 'total', 'status', 'created at']];
for (const order of db.orders.filter((o) => o.pickupDate === date)) {
  const articles = order.items
    .map((item) => {
      const product = db.products.find((p) => p.id === item.productId);
      return `${item.quantity} x ${product ? product.name : item.productId}`;
    })
    .join(' + ');
  const total = (order.totalCents / 100).toFixed(2).replace('.', ',');
  const created = order.createdAt.slice(0, 16).replace('T', ' ');
  rows.push([order.number, order.customer.name, order.customer.phone, articles, total, order.status, created]);
}

for (const row of rows) {
  console.log(row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(';'));
}
