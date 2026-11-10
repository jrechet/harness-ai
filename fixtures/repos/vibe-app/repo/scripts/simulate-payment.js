// Sends a signed PayFlux event to the local server, as PayFlux would.
//   node scripts/simulate-payment.js <orderId> [payment.succeeded]
import http from 'node:http';
import { config } from '../src/config.js';
import { sign } from '../src/lib/payflux.js';

const orderId = process.argv[2];
const type = process.argv[3] || 'payment.succeeded';
if (!orderId) {
  console.error('usage: node scripts/simulate-payment.js <orderId> [type]');
  process.exit(1);
}

const body = JSON.stringify({
  id: `evt_local_${Date.now()}`,
  type,
  created: Math.floor(Date.now() / 1000),
  data: { orderId, paymentId: `pay_local_${Date.now()}` },
});

const req = http.request(
  {
    host: 'localhost',
    port: config.port,
    path: '/webhooks/payflux',
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Payflux-Signature': sign(body) },
  },
  (res) => {
    let data = '';
    res.on('data', (chunk) => {
      data += chunk;
    });
    res.on('end', () => console.log(res.statusCode, data));
  },
);
req.on('error', (err) => console.error(err.message));
req.end(body);
