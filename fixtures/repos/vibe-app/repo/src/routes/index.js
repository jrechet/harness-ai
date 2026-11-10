import fs from 'node:fs';
import path from 'node:path';
import { config } from '../config.js';
import { sendJson } from '../lib/http.js';
import { summary } from '../services/stats.js';
import { readDb } from '../store.js';
import { createOrder, getOrder, listOrders } from './orders.js';
import { listProducts } from './products.js';
import { handleWebhook } from './webhook.js';

export async function route(req, res) {
  const url = new URL(req.url, 'http://localhost');
  const pathname = url.pathname;

  if (req.method === 'GET' && pathname === '/health') {
    return sendJson(res, 200, { ok: true });
  }
  if (req.method === 'GET' && (pathname === '/' || pathname === '/index.html')) {
    const html = fs.readFileSync(path.join(config.root, 'public', 'index.html'));
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(html);
  }
  if (req.method === 'GET' && pathname === '/favicon.ico') {
    res.writeHead(204);
    return res.end();
  }
  if (req.method === 'GET' && pathname === '/products') {
    return listProducts(req, res);
  }
  if (req.method === 'GET' && pathname === '/stats') {
    return sendJson(res, 200, summary(readDb()));
  }
  if (req.method === 'POST' && pathname === '/orders') {
    return createOrder(req, res);
  }
  if (req.method === 'GET' && pathname === '/orders') {
    return listOrders(req, res, url);
  }
  const orderMatch = pathname.match(/^\/orders\/([\w-]+)$/);
  if (req.method === 'GET' && orderMatch) {
    return getOrder(req, res, orderMatch[1]);
  }
  if (req.method === 'POST' && pathname === '/webhooks/payflux') {
    return handleWebhook(req, res);
  }
  return sendJson(res, 404, { error: 'not found' });
}
