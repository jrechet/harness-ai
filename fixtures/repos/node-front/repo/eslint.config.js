import vue from "eslint-plugin-vue";
import designTokens from "./tools/eslint-plugin-design-tokens/index.js";

export default [
  ...vue.configs["flat/recommended"],
  {
    files: ["src/**/*.{js,ts,vue}"],
    plugins: { "design-tokens": designTokens },
    rules: {
      "design-tokens/no-raw-color": "error",
      "vue/component-api-style": ["error", ["script-setup"]],
    },
  },
];
