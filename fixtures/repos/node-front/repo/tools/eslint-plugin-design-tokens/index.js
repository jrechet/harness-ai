// Règle maison : interdit les couleurs en dur (#hex, rgb(), hsl()) dans les templates Vue, les styles
// inline et le <script>. Porte la règle « pas de couleur en dur » d'AGENTS.md.
const RAW_COLOR = /#(?:[0-9a-f]{3}){1,2}\b|\brgba?\(|\bhsla?\(/i;

export default {
  rules: {
    "no-raw-color": {
      meta: { type: "problem", docs: { description: "Utiliser les tokens de src/styles/tokens.css" } },
      create(context) {
        const report = (node, value) => {
          if (typeof value === "string" && RAW_COLOR.test(value)) {
            context.report({ node, message: "Couleur en dur : utilise un token (var(--color-…))." });
          }
        };
        const scriptVisitor = { Literal: (node) => report(node, node.value) };
        // Le template Vue n'est pas dans l'AST ESTree : il faut passer par le visiteur de vue-eslint-parser.
        const templateVisitor = {
          VLiteral: (node) => report(node, node.value),
          "VAttribute[key.name='style'] VLiteral": (node) => report(node, node.value),
          Literal: (node) => report(node, node.value),
        };
        const services = context.sourceCode?.parserServices ?? context.parserServices;
        return services?.defineTemplateBodyVisitor
          ? services.defineTemplateBodyVisitor(templateVisitor, scriptVisitor)
          : scriptVisitor;
      },
    },
  },
};
