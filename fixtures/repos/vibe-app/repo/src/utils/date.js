import { config } from '../config.js';

// "samedi 14 mars"
export function toFrenchDate(value) {
  return new Date(value).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
}

export function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

// The shop is closed one day a week (config.shop.closedWeekday, 1 = Monday).
export function isClosed(dateIso) {
  return new Date(`${dateIso}T12:00:00`).getDay() === config.shop.closedWeekday;
}
