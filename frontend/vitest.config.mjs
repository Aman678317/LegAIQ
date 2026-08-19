import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "happy-dom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.test.{ts,tsx}"],
    globals: true,
  },
  resolve: {
    alias: {
      "@": "./src",
      "@/components": "./components",
      "@/lib": "./lib",
      "@/hooks": "./hooks",
      "@/types": "./types",
      "@/tokens": "./tokens",
    },
  },
});