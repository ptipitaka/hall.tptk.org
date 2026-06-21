import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: resolve(__dirname, "../static/dist"),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        edition: resolve(__dirname, "edition/main.ts"),
        master: resolve(__dirname, "master/main.ts"),
      },
      output: {
        entryFileNames: "[name].js",
      },
    },
  },
});
