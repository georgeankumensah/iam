import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    host: "0.0.0.0",
  },
  optimizeDeps: {
    exclude: ["@clet/oidc-client", "@clet/oidc-client/react"],
  },
  appType: "spa",
});
