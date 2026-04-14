import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Production build is emitted into the installed pi_deck package static dir.
const staticOut = "../backend/src/pi_deck/static";

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: staticOut,
    emptyOutDir: true,
    assetsDir: "assets",
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8756", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8756", changeOrigin: true },
      "/ws/events": { target: "ws://127.0.0.1:8756", ws: true, changeOrigin: true },
    },
  },
});
