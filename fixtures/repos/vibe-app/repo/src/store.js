import fs from 'node:fs';
import path from 'node:path';
import { config } from './config.js';

// The whole database is one JSON file: products with their stock, orders, stats.

export function freshDb() {
  const seed = JSON.parse(fs.readFileSync(config.seedFile, 'utf8'));
  return {
    products: seed.products,
    orders: [],
    nextOrderNumber: 1,
    stats: { requests: 0, lastRequestAt: null },
  };
}

export function readDb() {
  try {
    return JSON.parse(fs.readFileSync(config.dataFile, 'utf8'));
  } catch (err) {
    // first start, or the file cannot be parsed: start again from the catalogue
    return freshDb();
  }
}

export function writeDb(db) {
  fs.mkdirSync(path.dirname(config.dataFile), { recursive: true });
  fs.writeFileSync(config.dataFile, JSON.stringify(db, null, 2) + '\n');
}
