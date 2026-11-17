#!/usr/bin/env node
// Triggers release.yml. The kind of version is inferred from the branch name.
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";

const branch = execSync("git rev-parse --abbrev-ref HEAD").toString().trim();
const current = readFileSync("VERSION", "utf8").trim();
const [major, minor, patch] = current.split(".").map(Number);

let next;
if (branch === "develop") {
  next = `${major}.${minor + 1}.0`;          // a release from develop is always a minor
} else if (branch.startsWith("release/")) {
  next = branch.replace("release/", "");
} else if (branch.startsWith("feat/breaking-")) {
  next = `${major + 1}.0.0`;                 // the branch prefix decides on a major
} else {
  console.error(`Unexpected branch: ${branch}`);
  process.exit(1);
}

console.log(`Release ${current} -> ${next} from ${branch}`);
execSync(`gh workflow run release.yml -f version=${next} -f ref=${branch}`, { stdio: "inherit" });
console.log("Workflow triggered. Follow it with: gh run watch");
