/**
 * Tiny router for the v2 API.
 *
 *   const router = new Router();
 *   router.get('/orders/:id', (req, res, params) => { ... });
 *   const handled = await router.handle(req, res);
 */
export class Router {
  constructor() {
    this.routes = [];
  }

  add(method, pattern, handler) {
    const keys = [];
    const source = pattern.replace(/:(\w+)/g, (_, key) => {
      keys.push(key);
      return '([^/]+)';
    });
    this.routes.push({ method, regex: new RegExp(`^${source}$`), keys, handler });
    return this;
  }

  get(pattern, handler) {
    return this.add('GET', pattern, handler);
  }

  post(pattern, handler) {
    return this.add('POST', pattern, handler);
  }

  /** Runs the first matching route. Resolves to false when nothing matched. */
  async handle(req, res) {
    const { pathname } = new URL(req.url, 'http://localhost');
    for (const candidate of this.routes) {
      if (candidate.method !== req.method) continue;
      const match = pathname.match(candidate.regex);
      if (!match) continue;
      const params = Object.fromEntries(candidate.keys.map((key, i) => [key, decodeURIComponent(match[i + 1])]));
      await candidate.handler(req, res, params);
      return true;
    }
    return false;
  }
}
