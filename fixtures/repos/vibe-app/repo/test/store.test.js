import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { after, test } from 'node:test';

const dataFile = path.join(os.tmpdir(), `counter-store-${process.pid}.json`);
process.env.DATA_FILE = dataFile;
const { readDb, writeDb } = await import('../src/store.js');

after(() => fs.rmSync(dataFile, { force: true }));

test('without a data file the store starts from the catalogue', () => {
  const db = readDb();
  assert.equal(db.orders.length, 0);
  assert.equal(db.products.find((p) => p.id === 'croissant').priceCents, 120);
  assert.equal(fs.existsSync(dataFile), false);
});

test('what is written is read back', () => {
  const db = readDb();
  db.orders.push({ id: 'ord_test', status: 'pending', items: [], totalCents: 0 });
  db.products[0].stock = 3;
  writeDb(db);

  const again = readDb();
  assert.equal(again.orders[0].id, 'ord_test');
  assert.equal(again.products[0].stock, 3);
});
