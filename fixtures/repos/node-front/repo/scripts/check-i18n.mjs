#!/usr/bin/env node
// Checks that fr.json and en.json have exactly the same keys. Does not look at the templates.
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
  console.error(`Missing keys — en: ${missingEn.join(", ") || "none"} ; fr: ${missingFr.join(", ") || "none"}`);
  process.exit(1);
}
console.log(`i18n OK (${fr.size} keys)`);
