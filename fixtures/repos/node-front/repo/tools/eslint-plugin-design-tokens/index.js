// Règle maison : interdit les couleurs en dur (#hex, rgb(), hsl()) dans les templates et styles inline.
// Porte la règle « pas de couleur en dur » d'AGENTS.md.
const RAW_COLOR = /#(?:[0-9a-f]{3}){1,2}\b|\brgba?\(|\bhsla?\(/i;

export default {
  rules: {
    "no-raw-color": {
      meta: { type: "problem", docs: { description: "Utiliser les tokens de src/styles/tokens.css" } },
      create(context) {
        return {
          Literal(node) {
            if (typeof node.value === "string" && RAW_COLOR.test(node.value)) {
              context.report({ node, message: "Couleur en dur : utilise un token (var(--color-…))." });
            }
          },
        };
      },
    },
  },
};
