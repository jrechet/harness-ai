import { readDb, writeDb } from '../store.js';

// Request counter, shown by GET /stats.
export function countRequest() {
  const db = readDb();
  db.stats = db.stats || { requests: 0, lastRequestAt: null };
  db.stats.requests += 1;
  db.stats.lastRequestAt = new Date().toISOString();
  writeDb(db);
}

export function summary(db) {
  const byStatus = {};
  let revenueCents = 0;
  for (const order of db.orders) {
    byStatus[order.status] = (byStatus[order.status] || 0) + 1;
    if (order.status === 'paid') revenueCents += order.totalCents;
  }
  return { requests: db.stats.requests, lastRequestAt: db.stats.lastRequestAt, orders: byStatus, revenueCents };
}
