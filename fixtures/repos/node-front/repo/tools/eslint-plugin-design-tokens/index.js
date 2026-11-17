// In-house rule: forbids hard-coded colors (#hex, rgb(), hsl()) in Vue templates, inline
// styles and the <script>. Carries the "no hard-coded color" rule of AGENTS.md.
const RAW_COLOR = /#(?:[0-9a-f]{3}){1,2}\b|\brgba?\(|\bhsla?\(/i;

export default {
  rules: {
    "no-raw-color": {
      meta: { type: "problem", docs: { description: "Use the tokens of src/styles/tokens.css" } },
      create(context) {
        const report = (node, value) => {
          if (typeof value === "string" && RAW_COLOR.test(value)) {
            context.report({ node, message: "Hard-coded color: use a token (var(--color-…))." });
          }
        };
        const scriptVisitor = { Literal: (node) => report(node, node.value) };
        // The Vue template is not in the ESTree AST: it has to go through the vue-eslint-parser visitor.
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
