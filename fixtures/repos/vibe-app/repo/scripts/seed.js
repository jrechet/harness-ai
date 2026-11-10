// Puts the data file back to the demo catalogue: no orders, full stock.
//   node scripts/seed.js
import { config } from '../src/config.js';
import { freshDb, writeDb } from '../src/store.js';

writeDb(freshDb());
console.log(`data file reset: ${config.dataFile}`);
