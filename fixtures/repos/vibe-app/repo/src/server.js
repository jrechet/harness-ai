import http from 'node:http';
import { app } from './app.js';
import { config } from './config.js';
import { log } from './lib/logger.js';

const server = http.createServer(app);

server.listen(config.port, () => {
  log('info', `counter listening on http://localhost:${config.port} (data file: ${config.dataFile})`);
});
