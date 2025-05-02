import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    allowedHosts: ["seongjaeny.com"],
    // proxy: {
    //   "/api": {
    //     target: "http://localhost:5001",
    //     changeOrigin: true,
    //     rewrite: (path) => path.replace(/^\/api/, ""),
    //     secure: false,
    //     ws: true,
    //   },
    // },
  },
});
