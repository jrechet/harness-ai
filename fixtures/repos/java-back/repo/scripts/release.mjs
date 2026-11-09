#!/usr/bin/env node
// Déclenche release.yml. Le type de version est déduit du nom de la branche.
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";

const branch = execSync("git rev-parse --abbrev-ref HEAD").toString().trim();
const current = readFileSync("VERSION", "utf8").trim();
const [major, minor, patch] = current.split(".").map(Number);

let next;
if (branch === "develop") {
  next = `${major}.${minor + 1}.0`;          // une release depuis develop est toujours mineure
} else if (branch.startsWith("release/")) {
  next = branch.replace("release/", "");
} else if (branch.startsWith("feat/breaking-")) {
  next = `${major + 1}.0.0`;                 // le préfixe de branche décide d'une majeure
} else {
  console.error(`Branche inattendue : ${branch}`);
  process.exit(1);
}

console.log(`Release ${current} -> ${next} depuis ${branch}`);
execSync(`gh workflow run release.yml -f version=${next} -f ref=${branch}`, { stdio: "inherit" });
console.log("Workflow déclenché. Suis-le avec : gh run watch");
