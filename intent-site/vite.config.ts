import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  base: "/intent/",
  plugins: [react()],
  build: {
    outDir: "../intent-dist",
    emptyOutDir: true,
  },
});
