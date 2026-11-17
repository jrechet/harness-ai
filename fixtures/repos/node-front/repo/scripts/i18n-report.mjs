#!/usr/bin/env node
// Lists as JSON the keys present in fr.json and missing from en.json, for the agent-fix-i18n workflow.
import { readFileSync } from "node:fs";

function flatten(obj, prefix = "") {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === "object" && v !== null ? flatten(v, `${prefix}${k}.`) : [`${prefix}${k}`]);
}
const fr = JSON.parse(readFileSync("src/locales/fr.json", "utf8"));
const en = JSON.parse(readFileSync("src/locales/en.json", "utf8"));
const frKeys = flatten(fr);
const enKeys = new Set(flatten(en));
const missing = frKeys.filter((k) => !enKeys.has(k)).map((key) => ({ key, fr: key.split(".").reduce((o, p) => o?.[p], fr) }));
console.log(JSON.stringify(missing, null, 2));
