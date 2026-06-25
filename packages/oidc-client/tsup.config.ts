import { defineConfig } from "tsup";

export default defineConfig({
  entry: {
    index: "src/index.ts",
    "react/index": "react/index.ts",
  },
  format: ["esm"],
  dts: true,
  clean: true,
  external: ["oidc-client-ts", "react-oidc-context", "react", "react/jsx-runtime"],
  outDir: "dist",
});
