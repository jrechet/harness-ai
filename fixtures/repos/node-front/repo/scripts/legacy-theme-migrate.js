// Migration one-shot du thème v1 (variables SCSS) vers les tokens CSS, faite en 2024. Plus appelée.
const fs = require("fs");
const map = { "$primary": "--color-primary", "$danger": "--color-danger", "$text": "--color-text" };
for (const file of process.argv.slice(2)) {
  let css = fs.readFileSync(file, "utf8");
  for (const [from, to] of Object.entries(map)) css = css.replaceAll(from, `var(${to})`);
  fs.writeFileSync(file, css);
}
