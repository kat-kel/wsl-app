import { defineConfig, mergeConfig } from "vitest/config";

import viteConfig from "./vite.config";

// Inherits from vite.config.ts so the path aliases are defined once. Declaring
// them again here is what previously let tests resolve differently from the app.
export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test-setup.ts"],
    },
  }),
);
