#!/usr/bin/env node
// Triggers release.yml for a hotfix: same mechanics as release.mjs, patch number.
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";

const branch = execSync("git rev-parse --abbrev-ref HEAD").toString().trim();
if (!branch.startsWith("hotfix/")) {
  console.error("A hotfix starts from a hotfix/* branch");
  process.exit(1);
}
const current = readFileSync("VERSION", "utf8").trim();
const [major, minor, patch] = current.split(".").map(Number);
const next = `${major}.${minor}.${patch + 1}`;

console.log(`Hotfix ${current} -> ${next} from ${branch}`);
execSync(`gh workflow run release.yml -f version=${next} -f ref=${branch} -f hotfix=true`, { stdio: "inherit" });
