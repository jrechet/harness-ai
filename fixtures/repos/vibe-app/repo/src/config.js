import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const defaults = JSON.parse(fs.readFileSync(path.join(root, 'config', 'default.json'), 'utf8'));

// Environment variables win over config/default.json.
export const config = {
  root,
  port: Number(process.env.PORT || defaults.port),
  dataFile: path.resolve(root, process.env.DATA_FILE || defaults.dataFile),
  seedFile: path.join(root, 'data', 'seed.json'),
  shop: defaults.shop,
  payflux: {
    apiBase: defaults.payflux.apiBase,
    checkoutBase: defaults.payflux.checkoutBase,
    apiKey: process.env.PAYFLUX_API_KEY || defaults.payflux.apiKey,
    webhookSecret: process.env.PAYFLUX_WEBHOOK_SECRET || defaults.payflux.webhookSecret,
  },
};
