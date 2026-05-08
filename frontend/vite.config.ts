import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // GitHub Pages serves at /prereq-dependency/. Vercel/local dev use /.
  // Pass VITE_BASE=/prereq-dependency/ in the deploy workflow.
  base: process.env.VITE_BASE ?? "/",
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});
