const LEVELS = ['debug', 'info', 'warn', 'error'];

export function log(level, message) {
  const wanted = process.env.LOG_LEVEL || 'info';
  if (wanted === 'silent') return;
  if (LEVELS.indexOf(level) < LEVELS.indexOf(wanted)) return;
  const line = `[${new Date().toISOString()}] ${level.toUpperCase()} ${message}`;
  if (level === 'error') console.error(line);
  else console.log(line);
}
