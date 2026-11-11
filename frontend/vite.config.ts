import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vitest/config";

const VERCEL_REQUIRED_ENV = ["VITE_API_BASE_URL", "VITE_WS_BASE_URL"] as const;
const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0", "[::1]", "::1"]);

function assertVercelBuildEnv(): void {
  const missing = VERCEL_REQUIRED_ENV.filter((key) => !process.env[key]?.trim());
  if (missing.length) {
    throw new Error(
      `Vercel build is missing required Vite env vars: ${missing.join(", ")}. ` +
        "Set them to the Render backend URL before deploying.",
    );
  }
  for (const key of VERCEL_REQUIRED_ENV) {
    const value = process.env[key]!.trim();
    let url: URL;
    try {
      url = new URL(value);
    } catch {
      throw new Error(`${key} must be an absolute URL, got: ${value}`);
    }
    if (LOCAL_HOSTS.has(url.hostname.toLowerCase())) {
      throw new Error(
        `${key} points to localhost (${value}); use the deployed Render backend URL on Vercel.`,
      );
    }
    if (key === "VITE_API_BASE_URL" && url.protocol !== "https:") {
      throw new Error(`${key} must use https on Vercel, got: ${value}`);
    }
    if (key === "VITE_WS_BASE_URL" && !["https:", "wss:"].includes(url.protocol)) {
      throw new Error(`${key} must use https or wss on Vercel, got: ${value}`);
    }
    if (!url.pathname.replace(/\/+$/, "").endsWith("/api/v1")) {
      throw new Error(`${key} must include the /api/v1 path, got: ${value}`);
    }
  }
}

export default defineConfig(({ mode }) => {
  if (mode === "production" && process.env.VERCEL) {
    assertVercelBuildEnv();
  }
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    server: {
      port: 5173,
    },
    preview: {
      port: 4173,
    },
    build: {
      target: "es2022",
      chunkSizeWarningLimit: 1200,
      sourcemap: false,
    },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      css: false,
      include: ["src/**/*.{test,spec}.{ts,tsx}"],
      clearMocks: true,
      passWithNoTests: true,
    },
  };
});
