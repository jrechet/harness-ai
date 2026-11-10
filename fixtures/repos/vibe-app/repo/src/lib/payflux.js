import crypto from 'node:crypto';
import https from 'node:https';
import { config } from '../config.js';

// PayFlux signs each webhook: X-Payflux-Signature is the hex HMAC-SHA256 of the raw body.
export function sign(rawBody, secret = config.payflux.webhookSecret) {
  return crypto.createHmac('sha256', secret).update(rawBody).digest('hex');
}

export function verifySignature(rawBody, signature, secret = config.payflux.webhookSecret) {
  if (!signature) return false;
  const expected = Buffer.from(sign(rawBody, secret));
  const received = Buffer.from(String(signature));
  return expected.length === received.length && crypto.timingSafeEqual(expected, received);
}

// Link to the hosted payment page. Built locally: no call to PayFlux.
export function paymentUrl(order) {
  return `${config.payflux.checkoutBase}/${order.id}?amount=${order.totalCents}&currency=eur`;
}

// Creates a checkout through the PayFlux API. Not called anywhere yet:
// the shop's plan only has the static payment links above.
export function createCheckout(order) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      amount: order.totalCents,
      currency: 'eur',
      metadata: { orderId: order.id },
    });
    const req = https.request(
      `${config.payflux.apiBase}/checkouts`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${config.payflux.apiKey}`,
          'Content-Type': 'application/json',
        },
      },
      (res) => {
        let data = '';
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => {
          if (res.statusCode >= 300) return reject(new Error(`PayFlux answered ${res.statusCode}`));
          resolve(JSON.parse(data));
        });
      },
    );
    req.on('error', reject);
    req.end(body);
  });
}
