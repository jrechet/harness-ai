// Hidden acceptance helper of the cancel-order task. It starts the server the
// way the project does (`node src/server.js`), on its own port and its own data
// file, and talks to it over HTTP: only what is really wired answers.

import { spawn } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const SECRET = 'acceptance-only-webhook-secret';

function freePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.on('error', reject);
    probe.listen(0, () => {
      const { port } = probe.address();
      probe.close(() => resolve(port));
    });
  });
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export async function startShop() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'counter-acceptance-'));
  const port = await freePort();
  const child = spawn(process.execPath, ['src/server.js'], {
    cwd: ROOT,
    env: {
      ...process.env,
      PORT: String(port),
      DATA_FILE: path.join(dir, 'db.json'),
      PAYFLUX_WEBHOOK_SECRET: SECRET,
      LOG_LEVEL: 'silent',
    },
    stdio: ['ignore', 'ignore', 'inherit'],
  });
  const base = `http://localhost:${port}`;

  let up = false;
  for (let attempt = 0; attempt < 100 && !up; attempt += 1) {
    try {
      await fetch(`${base}/health`);
      up = true;
    } catch (err) {
      await sleep(50);
    }
  }
  if (!up) {
    child.kill();
    throw new Error('node src/server.js did not answer on PORT within 5 s');
  }

  async function json(method, pathname, body) {
    const res = await fetch(base + pathname, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    const text = await res.text();
    let parsed = null;
    try {
      parsed = JSON.parse(text);
    } catch (err) {
      parsed = null;
    }
    return { status: res.status, body: parsed };
  }

  return {
    // A product with enough stock, and how many units of it the shop has.
    async product() {
      const { body } = await json('GET', '/products');
      return body.find((p) => p.stock >= 10);
    },
    async stockOf(productId) {
      const { body } = await json('GET', '/products');
      return body.find((p) => p.id === productId).stock;
    },
    async order(productId, quantity) {
      const res = await json('POST', '/orders', {
        customer: { name: 'Ana Morel', phone: '0611223344' },
        items: [{ productId, quantity }],
        pickupDate: '2026-11-14',
      });
      if (res.status !== 201) throw new Error(`POST /orders answered ${res.status}`);
      return res.body;
    },
    read: (id) => json('GET', `/orders/${id}`),
    cancel: (id) => json('POST', `/orders/${id}/cancel`),
    // Delivers one PayFlux event, signed as PayFlux signs it. Returns the HTTP status.
    async deliver(event) {
      const raw = JSON.stringify(event);
      const res = await fetch(`${base}/webhooks/payflux`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Payflux-Signature': crypto.createHmac('sha256', SECRET).update(raw).digest('hex'),
        },
        body: raw,
      });
      await res.text();
      return res.status;
    },
    async stop() {
      const exited = new Promise((resolve) => child.once('exit', resolve));
      child.kill();
      await exited;
      fs.rmSync(dir, { recursive: true, force: true });
    },
  };
}

let sequence = 0;

export function paid(orderId) {
  sequence += 1;
  return {
    id: `evt_paid_${sequence}`,
    type: 'payment.succeeded',
    created: 1794650000 + sequence,
    data: { orderId, paymentId: `pay_${sequence}` },
  };
}

export function refunded(orderId) {
  sequence += 1;
  return {
    id: `evt_refund_${sequence}`,
    type: 'payment.refunded',
    created: 1794650000 + sequence,
    data: { orderId, paymentId: `pay_${sequence}` },
  };
}
