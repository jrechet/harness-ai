#!/usr/bin/env node
// Déclenche release.yml pour un hotfix : même mécanique que release.mjs, numéro de patch.
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";

const branch = execSync("git rev-parse --abbrev-ref HEAD").toString().trim();
if (!branch.startsWith("hotfix/")) {
  console.error("Un hotfix part d'une branche hotfix/*");
  process.exit(1);
}
const current = readFileSync("VERSION", "utf8").trim();
const [major, minor, patch] = current.split(".").map(Number);
const next = `${major}.${minor}.${patch + 1}`;

console.log(`Hotfix ${current} -> ${next} depuis ${branch}`);
execSync(`gh workflow run release.yml -f version=${next} -f ref=${branch} -f hotfix=true`, { stdio: "inherit" });
