// One-shot migration of the v1 theme (SCSS variables) to CSS tokens, done in 2024. No longer called.
const fs = require("fs");
const map = { "$primary": "--color-primary", "$danger": "--color-danger", "$text": "--color-text" };
for (const file of process.argv.slice(2)) {
  let css = fs.readFileSync(file, "utf8");
  for (const [from, to] of Object.entries(map)) css = css.replaceAll(from, `var(${to})`);
  fs.writeFileSync(file, css);
}
