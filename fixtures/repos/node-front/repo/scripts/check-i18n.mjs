#!/usr/bin/env node
// Vérifie que fr.json et en.json ont exactement les mêmes clés. Ne regarde pas les templates.
import { readFileSync } from "node:fs";

function flatten(obj, prefix = "") {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === "object" && v !== null ? flatten(v, `${prefix}${k}.`) : [`${prefix}${k}`]);
}
const fr = new Set(flatten(JSON.parse(readFileSync("src/locales/fr.json", "utf8"))));
const en = new Set(flatten(JSON.parse(readFileSync("src/locales/en.json", "utf8"))));
const missingEn = [...fr].filter((k) => !en.has(k));
const missingFr = [...en].filter((k) => !fr.has(k));
if (missingEn.length || missingFr.length) {
  console.error(`Clés manquantes — en: ${missingEn.join(", ") || "aucune"} ; fr: ${missingFr.join(", ") || "aucune"}`);
  process.exit(1);
}
console.log(`i18n OK (${fr.size} clés)`);
