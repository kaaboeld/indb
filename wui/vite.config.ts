import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const apiTarget = process.env.INDB_API_URL || "https://api.indb.tech";

export default defineConfig({
  base: "/wui/",
  plugins: [vue()],
  server: {
    port: 5174,
    proxy: {
      "/health": { target: apiTarget, changeOrigin: true },
      "/api": { target: apiTarget, changeOrigin: true },
      "/raft": { target: apiTarget, changeOrigin: true },
    },
  },
});
