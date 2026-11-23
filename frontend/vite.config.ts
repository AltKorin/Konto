import path from "node:path";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

// django-vite: w dev Django dokleja skrypty z :5173, w produkcji czyta dist/manifest.json
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/static/",
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  server: { port: 5174, strictPort: true, origin: "http://localhost:5174", cors: true },
  build: { manifest: "manifest.json", outDir: "dist", emptyOutDir: true, rollupOptions: { input: "src/main.tsx" } },
});
