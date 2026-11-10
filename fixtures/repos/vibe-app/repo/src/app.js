import { sendJson } from './lib/http.js';
import { log } from './lib/logger.js';
import { route } from './routes/index.js';
import { countRequest } from './services/stats.js';

// The request listener. src/server.js listens with it, the tests too.
export async function app(req, res) {
  const started = Date.now();
  try {
    countRequest();
    await route(req, res);
  } catch (err) {
    log('error', err.stack || String(err));
    if (!res.headersSent) sendJson(res, 500, { error: 'internal error' });
  }
  log('info', `${req.method} ${req.url} ${res.statusCode} ${Date.now() - started}ms`);
}
