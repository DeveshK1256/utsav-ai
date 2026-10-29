import nextConfig from "eslint-config-next/core-web-vitals";

const config = [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "dist/**",
      "out/**",
      "coverage/**",
      "tests/**",
      "scripts/**",
      "*.config.*",
      "vitest.config.mjs"
    ]
  },
  ...nextConfig,
  {
    rules: {
      "@next/next/no-page-custom-font": "off", // Google Fonts (Cinzel, Inter, Rozha One) are loaded in root layout
    }
  }
];

export default config;
