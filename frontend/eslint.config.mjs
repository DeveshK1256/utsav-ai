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
      "react-hooks/set-state-in-effect": "off", // Standard for React 18/19 client components fetching data / setting mounted state on mount
      "@next/next/no-page-custom-font": "off", // Google Fonts (Cinzel, Inter, Rozha One) are loaded in root layout
      "@next/next/no-img-element": "off", // Used for client-rendered Leaflet OSM tile elements, canvas blobs, and dynamic QR previews
    }
  }
];

export default config;
