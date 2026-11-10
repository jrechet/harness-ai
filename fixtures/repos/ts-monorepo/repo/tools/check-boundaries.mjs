#!/usr/bin/env node
// Fails when a workspace imports across a forbidden boundary:
//   - an app never imports another app (web <-> api);
//   - a package never imports an app;
//   - nobody reaches into a package's files: only its public entry.
// Usage: node tools/check-boundaries.mjs [--json]
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const IMPORT = /(?:import|export)\s[^'"]*?from\s*["']([^"']+)["']|import\(\s*["']([^"']+)["']\s*\)/g;

function* sourceFiles(dir) {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules") continue;
    const path = join(dir, name);
    if (statSync(path).isDirectory()) yield* sourceFiles(path);
    else if (/\.(ts|mts|js|mjs)$/.test(name)) yield path;
  }
}

// "apps/web" or "packages/shared" for a file under the repository.
function workspaceOf(path) {
  const [kind, name] = relative(root, path).split(sep);
  return (kind === "apps" || kind === "packages") && name ? `${kind}/${name}` : null;
}

function targetOf(file, specifier) {
  if (specifier.startsWith(".")) {
    const target = resolve(dirname(file), specifier);
    return { workspace: workspaceOf(target), deep: false };
  }
  const scoped = /^@deskly\/([\w-]+)(\/.+)?$/.exec(specifier);
  if (!scoped) return { workspace: null, deep: false };
  const workspace = ["apps", "packages"].map((kind) => `${kind}/${scoped[1]}`).find((w) => {
    try {
      return statSync(join(root, w)).isDirectory();
    } catch {
      return false;
    }
  });
  return { workspace: workspace ?? null, deep: Boolean(scoped[2]) };
}

const violations = [];
for (const kind of ["apps", "packages"]) {
  for (const file of sourceFiles(join(root, kind))) {
    const from = workspaceOf(file);
    for (const match of readFileSync(file, "utf8").matchAll(IMPORT)) {
      const specifier = match[1] ?? match[2];
      const { workspace: to, deep } = targetOf(file, specifier);
      if (!to || to === from) continue;
      const report = (rule) => violations.push({ file: relative(root, file), import: specifier, rule });
      if (to.startsWith("apps/")) report(from.startsWith("apps/") ? "an app never imports another app" : "a package never imports an app");
      else if (deep || specifier.startsWith(".")) report("import a package through its public entry only");
    }
  }
}

if (process.argv.includes("--json")) console.log(JSON.stringify(violations));
else for (const v of violations) console.error(`${v.file}: "${v.import}": ${v.rule}`);
process.exit(violations.length > 0 ? 1 : 0);
